"""Group new corroborating reports without rewriting existing complaints or evidence."""
from alembic import op

revision = "20261031_05"
down_revision = "20261020_04"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE complaints ADD COLUMN incident_id varchar(36) REFERENCES complaints(id)")
    op.execute("ALTER TABLE complaints ADD CONSTRAINT ck_complaint_incident CHECK "
               "(incident_id IS NULL OR (kind = 'complaint' AND incident_id <> id))")
    op.execute("CREATE INDEX ix_complaints_incident ON complaints (incident_id)")
    op.execute("CREATE INDEX ix_incident_candidates ON complaints (category_code, updated_at) "
               "WHERE kind = 'complaint' AND incident_id IS NULL")


def downgrade():
    op.drop_index("ix_incident_candidates", table_name="complaints")
    op.drop_index("ix_complaints_incident", table_name="complaints")
    op.drop_constraint("ck_complaint_incident", "complaints", type_="check")
    op.drop_column("complaints", "incident_id")
