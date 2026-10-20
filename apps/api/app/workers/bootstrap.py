"""Explicit, idempotent admin provisioning from server-only environment settings.

uv run python -m app.workers.bootstrap
Changing ADMIN_PASSWORD does not silently reset an existing administrator.
"""

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH, hasher
from app.db.session import session_factory
from app.models.civic import Category
from app.models.user import User
from app.services.catalog import CATEGORIES
from app.services.road_catalog import seed_main_roads


def bootstrap(db, settings):
    seed_main_roads(db)
    for code, label, priority in CATEGORIES:
        if not db.get(Category, code):
            db.add(Category(code=code, label=label, base_priority=priority))
    if not settings.admin_email and not settings.admin_password:
        return "Catalog ready; set ADMIN_EMAIL and ADMIN_PASSWORD to provision the mayor."
    from pydantic import EmailStr, TypeAdapter

    email = str(TypeAdapter(EmailStr).validate_python(settings.admin_email)).lower()
    if not PASSWORD_MIN_LENGTH <= len(settings.admin_password) <= PASSWORD_MAX_LENGTH:
        raise ValueError(
            f"ADMIN_PASSWORD must be {PASSWORD_MIN_LENGTH}–{PASSWORD_MAX_LENGTH} characters"
        )
    existing = db.scalar(select(User).where(User.email == email).with_for_update())
    if existing:
        if existing.role != "admin":
            raise ValueError(
                "ADMIN_EMAIL belongs to a non-admin; refusing automatic privilege escalation"
            )
        return "Administrator already provisioned; password unchanged."
    db.add(
        User(
            email=email,
            name=settings.admin_name,
            role="admin",
            email_verified=True,
            password_hash=hasher.hash(settings.admin_password),
        )
    )
    return "Administrator provisioned."


if __name__ == "__main__":
    with session_factory()() as db:
        message = bootstrap(db, get_settings())
        db.commit()
        print(message)
