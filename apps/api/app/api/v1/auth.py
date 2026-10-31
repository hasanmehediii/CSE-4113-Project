import hmac
import re
import time
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from redis.exceptions import RedisError
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.dependencies import CurrentSession, CurrentUser, Database, require_csrf
from app.core.rate_limit import auth_ip_limit, enforce
from app.core.security import digest, hasher, random_token, verify_password
from app.models.civic import WorkerApplication
from app.models.user import AuthSession, Identity, PasswordHistory, User
from app.schemas.user import (
    EmailInput,
    GoogleInput,
    LoginInput,
    RecoveryInput,
    RegisterInput,
    ResetInput,
    TokenInput,
    UserOutput,
)
from app.services.auth_service import (
    audit,
    change_password,
    clear_cookies,
    consume_action_token,
    create_action_token,
    set_csrf,
    start_session,
)
from app.services.email_service import send_action_email
from app.services.google_provider import GoogleProvider, get_google_provider
from app.services.worker_service import submit_application

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    dependencies=[Depends(auth_ip_limit), Depends(require_csrf)],
)
GENERIC = {"message": "If eligible, an email will be sent. Check your inbox."}


def account_output(db, user):
    output = UserOutput.model_validate(user)
    application = db.get(WorkerApplication, user.id)
    output.worker_application_status = application.status if application else None
    return output


def account_limit(request: Request, email: str, scope: str, capacity=5, period=900):
    enforce(request, scope, email, capacity, period)


@router.get("/csrf")
def csrf(request: Request, response: Response):
    return {
        "csrf_token": set_csrf(response, request.cookies.get(get_settings().session_cookie, ""))
    }


@router.post("/register", status_code=202)
def register(data: RegisterInput, request: Request, db: Database, tasks: BackgroundTasks):
    account_limit(request, data.email, "register", 3, 3600)
    password_hash = hasher.hash(data.password)
    user = db.scalar(select(User).where(User.email == data.email))
    if user:
        return GENERIC
    user = User(
        email=data.email,
        name=data.name,
        password_hash=password_hash,
        phone=data.phone,
        date_of_birth=data.date_of_birth,
        blood_group=data.blood_group,
    )
    db.add(user)
    try:
        db.flush()
        if data.account_type == "worker":
            submit_application(db, user.id, data.worker_identity)
        token = create_action_token(db, user, "verify")
        db.commit()
    except IntegrityError:
        db.rollback()
        return GENERIC
    tasks.add_task(send_action_email, user.email, token, "verify")
    audit("register", user.id)
    return GENERIC


@router.post("/login", response_model=UserOutput)
def login(data: LoginInput, request: Request, response: Response, db: Database):
    account_limit(request, data.identifier, "login")
    user = db.scalar(
        select(User)
        .where(or_(User.email == data.identifier, User.phone == data.identifier))
        .with_for_update()
    )
    if (
        not verify_password(user.password_hash if user else None, data.password)
        or not user
        or not user.is_active
    ):
        audit("login_failed")
        raise HTTPException(401, "Invalid email/phone or password")
    if hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hasher.hash(data.password)
        db.flush()
    start_session(db, user, request, response)
    return account_output(db, user)


@router.get("/me", response_model=UserOutput)
def me(user: CurrentUser, db: Database):
    return account_output(db, user)


@router.post("/logout")
def logout(request: Request, response: Response, db: Database):
    token = request.cookies.get(get_settings().session_cookie, "")
    db.execute(
        update(AuthSession).where(AuthSession.token_hash == digest(token)).values(revoked=True)
    )
    db.commit()
    clear_cookies(response)
    return {"message": "Logged out"}


@router.post("/logout-all")
def logout_all(user: CurrentUser, db: Database, response: Response):
    db.refresh(user, with_for_update=True)
    db.execute(update(AuthSession).where(AuthSession.user_id == user.id).values(revoked=True))
    db.commit()
    clear_cookies(response)
    audit("logout_all", user.id)
    return {"message": "All sessions revoked"}


@router.get("/sessions")
def sessions(user: CurrentUser, current: CurrentSession, db: Database):
    now = int(time.time())
    rows = db.scalars(
        select(AuthSession).where(
            AuthSession.user_id == user.id,
            AuthSession.revoked.is_(False),
            AuthSession.expires_at > now,
            AuthSession.last_seen_at > now - get_settings().session_idle_seconds,
        )
    ).all()
    return [
        {
            "id": row.id,
            "created_at": row.created_at,
            "last_seen_at": row.last_seen_at,
            "expires_at": row.expires_at,
            "current": row.id == current.id,
        }
        for row in rows
    ]


@router.delete("/sessions/{session_id}")
def revoke_session(session_id: str, user: CurrentUser, db: Database):
    result = db.execute(
        update(AuthSession)
        .where(AuthSession.id == session_id, AuthSession.user_id == user.id)
        .values(revoked=True)
    )
    if not result.rowcount:
        raise HTTPException(404, "Session not found")
    audit("session_revoked", user.id)
    return {"message": "Session revoked"}


def request_email(data: EmailInput, request: Request, db, tasks, purpose: str):
    account_limit(request, data.email, f"email-{purpose}", 3, 3600)
    user = db.scalar(select(User).where(User.email == data.email).with_for_update())
    if user and user.is_active and (purpose == "reset" or not user.email_verified):
        token = create_action_token(db, user, purpose)
        db.commit()
        tasks.add_task(send_action_email, user.email, token, purpose)
    return GENERIC


@router.post("/forgot-password", status_code=202)
def forgot_password(data: EmailInput, request: Request, db: Database, tasks: BackgroundTasks):
    return request_email(data, request, db, tasks, "reset")


@router.post("/recover", status_code=202)
def recover(data: RecoveryInput, request: Request, db: Database, tasks: BackgroundTasks):
    account_limit(request, data.email, "recovery", 3, 3600)
    user = db.scalar(select(User).where(User.email == data.email).with_for_update())
    history = (
        db.scalars(
            select(PasswordHistory)
            .where(PasswordHistory.user_id == user.id)
            .order_by(PasswordHistory.retired_at.desc())
            .limit(4)
        ).all()
        if user
        else []
    )
    # Always perform five Argon2 checks; never disclose which recovery factor matched.
    hashes = [user.password_hash if user else None] + [row.password_hash for row in history]
    hashes += [None] * (5 - len(hashes))
    matches = [verify_password(stored, data.remembered_password) for stored in hashes]
    matched = any(matches)
    if user and user.is_active and user.date_of_birth == data.date_of_birth and matched:
        token = create_action_token(db, user, "reset")
        db.commit()
        tasks.add_task(send_action_email, user.email, token, "reset")
    return GENERIC


@router.post("/resend-verification", status_code=202)
def resend_verification(data: EmailInput, request: Request, db: Database, tasks: BackgroundTasks):
    return request_email(data, request, db, tasks, "verify")


@router.post("/verify-email")
def verify_email(data: TokenInput, db: Database):
    user = consume_action_token(db, data.token, "verify")
    user.email_verified = True
    audit("email_verified", user.id)
    return {"message": "Email verified"}


@router.post("/reset-password")
def reset_password(data: ResetInput, db: Database, response: Response):
    user = consume_action_token(db, data.token, "reset")
    change_password(db, user, data.password)
    user.email_verified = True  # Possession of this email-delivered token proves ownership.
    db.execute(update(AuthSession).where(AuthSession.user_id == user.id).values(revoked=True))
    db.commit()
    clear_cookies(response)
    audit("password_reset", user.id)
    return {"message": "Password changed. Sign in again."}


@router.post("/google/nonce")
def google_nonce(request: Request):
    if not get_settings().google_client_id:
        raise HTTPException(503, "Google sign-in is not configured")
    nonce = random_token()
    binding = digest(request.cookies[get_settings().csrf_cookie])
    try:
        request.app.state.limiter.redis.set(f"google-nonce:{digest(nonce)}", binding, ex=300)
    except RedisError:
        raise HTTPException(503, "Authentication temporarily unavailable")
    return {"nonce": nonce}


@router.post("/google", response_model=UserOutput)
def google_login(
    data: GoogleInput,
    request: Request,
    response: Response,
    db: Database,
    provider: Annotated[GoogleProvider, Depends(get_google_provider)],
):
    claims = provider.verify(data.credential)
    if not isinstance(claims.get("nonce"), str) or not hmac.compare_digest(
        claims["nonce"], data.nonce
    ):
        raise HTTPException(401, "Invalid Google nonce")
    try:
        binding = request.app.state.limiter.redis.getdel(f"google-nonce:{digest(data.nonce)}")
    except RedisError:
        raise HTTPException(503, "Authentication temporarily unavailable")
    expected = digest(request.cookies[get_settings().csrf_cookie]).encode()
    if not binding or not hmac.compare_digest(binding, expected):
        raise HTTPException(401, "Invalid or expired Google nonce")
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject or len(subject) > 255:
        raise HTTPException(401, "Invalid Google identity")
    identity = db.scalar(
        select(Identity).where(Identity.provider == "google", Identity.subject == subject)
    )
    if identity:
        user = db.get(User, identity.user_id)
    else:
        email = str(claims.get("email", "")).lower()
        # Only accept authoritative Google email identities for initial signup.
        if not claims.get("email_verified") or not (
            email.endswith("@gmail.com") or claims.get("hd")
        ):
            raise HTTPException(400, "Use email registration to verify this email address")
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(email) > 320:
            raise HTTPException(401, "Invalid Google identity")
        if db.scalar(select(User).where(User.email == email)):
            raise HTTPException(
                409, "Sign in with your existing method; automatic linking is disabled"
            )
        user = User(email=email, name=str(claims.get("name") or "User")[:100], email_verified=True)
        db.add(user)
        try:
            db.flush()
            db.add(Identity(user_id=user.id, provider="google", subject=subject))
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Account already exists; retry sign-in")
    start_session(db, user, request, response)
    return account_output(db, user)
