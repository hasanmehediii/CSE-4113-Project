"""Shared account/session lifecycle; providers never create their own session format."""

import logging
import time

from fastapi import HTTPException, Request, Response
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import digest, make_csrf, random_token
from app.models.user import ActionToken, AuthSession, User

logger = logging.getLogger("auth.audit")
logger.setLevel(logging.INFO)


def audit(event: str, user_id: str | None = None):
    logger.info("auth_event=%s user_id=%s", event, user_id or "anonymous")


def set_csrf(response: Response, session_token: str = "") -> str:
    settings = get_settings()
    token = make_csrf(settings.auth_secret, session_token)
    response.set_cookie(
        settings.csrf_cookie,
        token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
        max_age=settings.csrf_seconds,
    )
    return token


def start_session(db: Session, user: User, request: Request, response: Response):
    settings = get_settings()
    # Lock the account to serialize session issuance against password reset/logout-all.
    db.refresh(user, with_for_update=True)
    if not user.is_active:
        raise HTTPException(401, "Authentication required")
    old = request.cookies.get(settings.session_cookie)
    if old:
        db.execute(
            update(AuthSession).where(AuthSession.token_hash == digest(old)).values(revoked=True)
        )
    token = random_token()
    now = int(time.time())
    db.add(
        AuthSession(
            token_hash=digest(token),
            user_id=user.id,
            created_at=now,
            last_seen_at=now,
            expires_at=now + settings.session_absolute_seconds,
        )
    )
    db.commit()
    response.set_cookie(
        settings.session_cookie,
        token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
        max_age=settings.session_absolute_seconds,
    )
    set_csrf(response, token)
    audit("login", user.id)


def clear_cookies(response: Response):
    settings = get_settings()
    for name in (settings.session_cookie, settings.csrf_cookie):
        response.delete_cookie(
            name, path="/", secure=settings.cookie_secure, httponly=True, samesite="lax"
        )


def create_action_token(db: Session, user: User, purpose: str) -> str:
    token = random_token()
    # Caller holds the user lock; replacing previous tokens prevents stale-link reuse.
    db.execute(
        delete(ActionToken).where(ActionToken.user_id == user.id, ActionToken.purpose == purpose)
    )
    lifetime = 900 if purpose == "reset" else 86400
    db.add(
        ActionToken(
            token_hash=digest(token),
            user_id=user.id,
            purpose=purpose,
            expires_at=int(time.time()) + lifetime,
        )
    )
    return token


def consume_action_token(db: Session, raw: str, purpose: str) -> User:
    hashed = digest(raw)
    candidate = db.scalar(
        select(ActionToken).where(ActionToken.token_hash == hashed, ActionToken.purpose == purpose)
    )
    if candidate is None:
        raise HTTPException(400, "Invalid or expired token")
    user = db.scalar(select(User).where(User.id == candidate.user_id).with_for_update())
    # DELETE RETURNING makes consumption single-use even under concurrent requests.
    consumed = db.execute(
        delete(ActionToken)
        .where(
            ActionToken.token_hash == hashed,
            ActionToken.purpose == purpose,
            ActionToken.expires_at > int(time.time()),
        )
        .returning(ActionToken.user_id)
    ).scalar_one_or_none()
    if not consumed or not user or not user.is_active:
        raise HTTPException(400, "Invalid or expired token")
    return user
