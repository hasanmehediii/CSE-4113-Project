"""Generate only the fresh-install schema snapshot; never rewrite released migrations.

Run from the repository root: apps/api/.venv/Scripts/python db/generate_schema.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))

from alembic.config import Config  # noqa: E402
from alembic.script import ScriptDirectory  # noqa: E402
from sqlalchemy.dialects import postgresql  # noqa: E402
from sqlalchemy.schema import CreateIndex, CreateTable  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.models import civic, user  # noqa: E402, F401
from app.services.catalog import CATEGORIES  # noqa: E402

EXTRAS = """
CREATE EXTENSION IF NOT EXISTS cube;
CREATE EXTENSION IF NOT EXISTS earthdistance;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX ix_complaints_geo ON complaints USING gist (ll_to_earth(latitude, longitude));
CREATE INDEX ix_roads_geo ON roads USING gist (ll_to_earth(latitude, longitude));
CREATE INDEX ix_worker_locations_geo ON worker_locations USING gist (ll_to_earth(latitude, longitude));
CREATE INDEX ix_complaints_search ON complaints USING gin ((title || ' ' || description || ' ' || address) gin_trgm_ops);
CREATE INDEX ix_users_name_search ON users USING gin (name gin_trgm_ops);
CREATE INDEX ix_complaints_open ON complaints (created_at DESC) WHERE status IN ('open','assigned','disputed');
CREATE INDEX ix_users_role_active ON users (role, is_active);
CREATE INDEX ix_password_history_recent ON password_history (user_id, retired_at DESC);
ALTER TABLE complaints CLUSTER ON ix_complaints_road_time;
"""
HEADER = """-- DubsiBhai PostgreSQL 17 schema. Generated from SQLAlchemy metadata.
-- Fresh EMPTY database only: psql -v ON_ERROR_STOP=1 -f db/schema.sql
-- Existing databases: use uv run alembic upgrade head instead.
-- Run app.workers.bootstrap after import to seed roads and an optional mayor.
-- All *_at columns are UTC Unix seconds, except password_history.retired_at (microseconds).
-- UUID-shaped IDs remain varchar(36) for compatibility with existing auth migrations.
-- No plaintext passwords, NID numbers, image bytes, or point balance caches.
BEGIN;
"""


def generate_snapshot():
    dialect = postgresql.dialect()
    config = Config(str(ROOT / "apps/api/alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "apps/api/alembic"))
    revision = ScriptDirectory.from_config(config).get_current_head()
    statements = []
    for table in Base.metadata.sorted_tables:
        statements.append(str(CreateTable(table).compile(dialect=dialect)).strip() + ";\n")
        statements.extend(
            str(CreateIndex(index).compile(dialect=dialect)) + ";\n"
            for index in sorted(table.indexes, key=lambda item: item.name)
        )
    seed = "INSERT INTO complaint_categories (code, label, base_priority) VALUES\n" + ",\n".join(
        f"('{code}', '{label}', {priority})" for code, label, priority in CATEGORIES
    ) + ";\n"
    snapshot = (
        HEADER + "\n".join(statements) + EXTRAS + seed
        + "CREATE TABLE alembic_version (version_num varchar(32) PRIMARY KEY);\n"
        + f"INSERT INTO alembic_version VALUES ('{revision}');\nCOMMIT;\n"
    )
    return "\n".join(line.rstrip() for line in snapshot.splitlines()) + "\n"


if __name__ == "__main__":
    (ROOT / "db/schema.sql").write_text(generate_snapshot(), encoding="utf-8")
    print("Generated db/schema.sql; existing migrations are unchanged.")
