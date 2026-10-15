from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings


@lru_cache
def session_factory():
    settings = get_settings()
    return sessionmaker(
        create_engine(
            settings.database_url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 5}
            if settings.database_url.startswith("postgresql")
            else {},
        ),
        expire_on_commit=False,
    )


def get_db():
    with session_factory()() as db:
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
