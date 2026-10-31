"""Preserve historical completions while making the current work cycle explicit."""
from alembic import op

revision = "20261031_06"
down_revision = "20261031_05"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE resolutions ADD COLUMN superseded_at bigint")
    # Repair incidents already resolved by an old completion while replacement
    # work is still active. Preserve the replacement assignment and its owner.
    op.execute("""
        WITH active AS MATERIALIZED (
            SELECT c.id FROM complaints c
            WHERE c.status <> 'false'
              AND EXISTS (SELECT 1 FROM assignments a WHERE a.complaint_id = c.id AND a.status = 'active')
        )
        UPDATE complaints SET status = 'assigned'
        WHERE id IN (SELECT id FROM active) OR incident_id IN (SELECT id FROM active)
    """)
    # Legacy rows lack an explicit current marker. Retire completions belonging
    # to unfinished/cancelled work, reopened incidents, or older submissions.
    # Equal newest timestamps are ambiguous: retain the evidence, not a guessed
    # winner based on random UUID order. Such incidents reopen for a fresh job.
    op.execute("""
        UPDATE resolutions r SET superseded_at = EXTRACT(EPOCH FROM NOW())::bigint
        WHERE EXISTS (SELECT 1 FROM assignments a WHERE a.id = r.assignment_id AND a.status <> 'completed')
           OR EXISTS (SELECT 1 FROM assignments a WHERE a.complaint_id = r.complaint_id AND a.status = 'active')
           OR EXISTS (SELECT 1 FROM complaints c WHERE c.id = r.complaint_id AND c.status IN ('open', 'assigned'))
           OR EXISTS (SELECT 1 FROM resolutions newer WHERE newer.complaint_id = r.complaint_id
                      AND newer.id <> r.id AND newer.created_at >= r.created_at)
    """)
    op.execute("""
        WITH reopen AS MATERIALIZED (
            SELECT c.id FROM complaints c
            WHERE c.status IN ('awaiting_confirmation', 'resolved', 'disputed')
              AND EXISTS (SELECT 1 FROM resolutions r WHERE r.complaint_id = c.id)
              AND NOT EXISTS (SELECT 1 FROM resolutions r WHERE r.complaint_id = c.id AND r.superseded_at IS NULL)
              AND NOT EXISTS (SELECT 1 FROM assignments a WHERE a.complaint_id = c.id AND a.status = 'active')
        )
        UPDATE complaints SET status = 'open'
        WHERE id IN (SELECT id FROM reopen) OR incident_id IN (SELECT id FROM reopen)
    """)
    op.execute("CREATE UNIQUE INDEX uq_resolution_current ON resolutions (complaint_id) WHERE superseded_at IS NULL")


def downgrade():
    op.drop_index("uq_resolution_current", table_name="resolutions")
    op.drop_column("resolutions", "superseded_at")
