import hmac
import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import digest, valid_csrf
from app.db.session import get_db
from app.models.user import AuthSession, User

Database = Annotated[Session, Depends(get_db)]


def require_csrf(request: Request):
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    settings = get_settings()
    if request.headers.get("origin") not in settings.api_cors_origins:
        raise HTTPException(403, "Untrusted request origin")
    token = request.headers.get("x-csrf-token", "")
    cookie = request.cookies.get(settings.csrf_cookie, "")
    session = request.cookies.get(settings.session_cookie, "")
    if (
        not token
        or not hmac.compare_digest(token, cookie)
        or not valid_csrf(token, settings.auth_secret, settings.csrf_seconds, session)
    ):
        raise HTTPException(403, "Invalid CSRF token")


def current_session(request: Request, db: Database) -> AuthSession:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie, "")
    now = int(time.time())
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == digest(token)))
    if (
        not session
        or session.revoked
        or session.expires_at <= now
        or (session.last_seen_at + settings.session_idle_seconds <= now)
    ):
        raise HTTPException(401, "Authentication required")
    # Update only last_seen, never overwrite revocation from a concurrent logout.
    db.execute(
        update(AuthSession)
        .where(AuthSession.id == session.id, AuthSession.last_seen_at < now)
        .values(last_seen_at=now)
    )
    return session


def current_user(db: Database, session: Annotated[AuthSession, Depends(current_session)]) -> User:
    user = db.get(User, session.user_id)
    if not user or not user.is_active:
        raise HTTPException(401, "Authentication required")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
CurrentSession = Annotated[AuthSession, Depends(current_session)]


def verified_user(user: CurrentUser) -> User:
    if not user.email_verified:
        raise HTTPException(403, "Verify your email first")
    return user


def require_roles(*roles: str):
    def dependency(user: Annotated[User, Depends(verified_user)]):
        if user.role not in roles:
            raise HTTPException(403, "Insufficient permissions")
        return user

    return dependency
