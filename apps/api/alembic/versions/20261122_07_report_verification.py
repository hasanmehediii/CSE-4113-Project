"""Verified reports earn points; disliked reports go to administrator review."""
from alembic import op

revision = "20261122_07"
down_revision = "20261031_06"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE complaints ADD COLUMN verified_at bigint")
    op.execute("ALTER TABLE moderation_cases DROP CONSTRAINT ck_moderation_kind")
    op.execute(
        "ALTER TABLE moderation_cases ADD CONSTRAINT ck_moderation_kind "
        "CHECK (kind IN ('false_complaint','worker_dispute','disliked_report'))"
    )


def downgrade():
    op.execute("DELETE FROM moderation_cases WHERE kind = 'disliked_report'")
    op.execute("ALTER TABLE moderation_cases DROP CONSTRAINT ck_moderation_kind")
    op.execute(
        "ALTER TABLE moderation_cases ADD CONSTRAINT ck_moderation_kind "
        "CHECK (kind IN ('false_complaint','worker_dispute'))"
    )
    op.execute("ALTER TABLE complaints DROP COLUMN verified_at")
