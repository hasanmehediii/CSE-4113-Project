"""Generate a reviewable fresh-install SQL snapshot and frozen civic migration.

Run from repo root: apps/api/.venv/Scripts/python db/generate_schema.py
Do not regenerate the migration after it has been released.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from sqlalchemy.schema import CreateIndex, CreateTable  # noqa: E402
from sqlalchemy.dialects import postgresql  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.models import civic, user  # noqa: E402, F401
from app.services.catalog import CATEGORIES  # noqa: E402

dialect = postgresql.dialect()
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
SEED = "INSERT INTO complaint_categories (code, label, base_priority) VALUES\n" + ",\n".join(
    f"('{code}', '{label}', {priority})" for code, label, priority in CATEGORIES
) + ";\n"


def table_sql(table):
    return str(CreateTable(table).compile(dialect=dialect)).strip() + ";\n" + "\n".join(
        str(CreateIndex(index).compile(dialect=dialect)) + ";"
        for index in sorted(table.indexes, key=lambda idx: idx.name)
    ) + "\n"


header = """-- DubsiBhai PostgreSQL 17 schema. Generated from SQLAlchemy metadata.
-- Fresh EMPTY database only: psql -v ON_ERROR_STOP=1 -f db/schema.sql
-- Existing databases: use `uv run alembic upgrade head` instead.
-- All *_at columns are UTC Unix seconds, except password_history.retired_at (microseconds).
-- UUID-shaped IDs remain varchar(36) for compatibility with existing auth migrations.
-- No plaintext passwords, NID numbers, image bytes, or point balance caches.
-- CLUSTER preference is recorded below; physical clustering is explicit maintenance.
BEGIN;
"""
tables = Base.metadata.sorted_tables
(ROOT / "db/schema.sql").write_text(
    header + "\n".join(table_sql(table) for table in tables) + EXTRAS + SEED
    + "CREATE TABLE alembic_version (version_num varchar(32) PRIMARY KEY);\n"
    + "INSERT INTO alembic_version VALUES ('20261015_03');\nCOMMIT;\n", encoding="utf-8"
)
old = {"users", "auth_identities", "auth_sessions", "auth_action_tokens", "complaint_predictions"}
upgrade_sql = """
ALTER TABLE users ADD COLUMN phone varchar(16) UNIQUE;
ALTER TABLE users ADD COLUMN date_of_birth date;
ALTER TABLE users ADD COLUMN blood_group varchar(3);
ALTER TABLE users ADD CONSTRAINT ck_user_role CHECK (role IN ('citizen','worker','admin'));
ALTER TABLE users ADD CONSTRAINT ck_blood_group CHECK (blood_group IS NULL OR blood_group IN ('A+','A-','B+','B-','AB+','AB-','O+','O-'));
""" + "\n".join(table_sql(t) for t in tables if t.name not in old) + EXTRAS + SEED
downgrade_sql = "\n".join(f"DROP TABLE {t.name};" for t in reversed(tables) if t.name not in old)
downgrade_sql += """
DROP INDEX ix_users_role_active;
DROP INDEX ix_users_name_search;
ALTER TABLE users DROP CONSTRAINT ck_blood_group;
ALTER TABLE users DROP CONSTRAINT ck_user_role;
ALTER TABLE users DROP COLUMN blood_group;
ALTER TABLE users DROP COLUMN date_of_birth;
ALTER TABLE users DROP COLUMN phone;
"""
migration = '''"""Civic workflows, profiles, password history and spatial/search indexes.

Frozen SQL snapshot; existing auth rows and sessions are preserved.
"""
from alembic import op

revision = "20261015_02"
down_revision = "20260926_01"
branch_labels = None
depends_on = None

UPGRADE = %r
DOWNGRADE = %r


def execute_statements(sql):
    for statement in sql.split(";"):
        if statement.strip():
            op.execute(statement)


def upgrade():
    execute_statements(UPGRADE)


def downgrade():
    execute_statements(DOWNGRADE)
''' % (upgrade_sql, downgrade_sql)
(ROOT / "apps/api/alembic/versions/20261015_02_civic.py").write_text(migration, encoding="utf-8")
prediction_sql = table_sql(Base.metadata.tables["complaint_predictions"])
(ROOT / "apps/api/alembic/versions/20261015_03_predictions.py").write_text(
    '''"""Existing classifier integration with durable retry state."""
from alembic import op

revision = "20261015_03"
down_revision = "20261015_02"
branch_labels = None
depends_on = None


def upgrade():
    for statement in %r.split(";"):
        if statement.strip():
            op.execute(statement)
    op.execute("INSERT INTO complaint_predictions (complaint_id, status, attempts, next_attempt_at) SELECT id, 'pending', 0, 0 FROM complaints WHERE kind = 'complaint'")


def downgrade():
    op.drop_table("complaint_predictions")
''' % prediction_sql, encoding="utf-8")
print("Generated db/schema.sql and frozen civic migration")
