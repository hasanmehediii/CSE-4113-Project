"""Prune expired/revoked auth rows. Schedule this command periodically in deployment."""

import time

from sqlalchemy import delete, or_

from app.core.config import get_settings
from app.db.session import session_factory
from app.models.user import ActionToken, AuthSession


def prune():
    now = int(time.time())
    idle_cutoff = now - get_settings().session_idle_seconds
    with session_factory()() as db:
        db.execute(delete(ActionToken).where(ActionToken.expires_at <= now))
        db.execute(
            delete(AuthSession).where(
                or_(
                    AuthSession.revoked.is_(True),
                    AuthSession.expires_at <= now,
                    AuthSession.last_seen_at <= idle_cutoff,
                )
            )
        )
        db.commit()


if __name__ == "__main__":
    prune()
