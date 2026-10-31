"""Existing classifier integration with durable retry state."""
from alembic import op

revision = "20261015_03"
down_revision = "20261015_02"
branch_labels = None
depends_on = None


def upgrade():
    for statement in "CREATE TABLE complaint_predictions (\n\tcomplaint_id VARCHAR(36) NOT NULL, \n\tstatus VARCHAR(10) NOT NULL, \n\tpredicted_category VARCHAR(40), \n\tconfidence FLOAT, \n\tmodel_version VARCHAR(100), \n\tattempts INTEGER NOT NULL, \n\tnext_attempt_at BIGINT NOT NULL, \n\tclassified_at BIGINT, \n\tPRIMARY KEY (complaint_id), \n\tCONSTRAINT ck_prediction_status CHECK (status IN ('pending','ready')), \n\tCONSTRAINT ck_prediction_confidence CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1), \n\tFOREIGN KEY(complaint_id) REFERENCES complaints (id), \n\tFOREIGN KEY(predicted_category) REFERENCES complaint_categories (code)\n);\nCREATE INDEX ix_prediction_retry ON complaint_predictions (status, next_attempt_at);\n".split(";"):
        if statement.strip():
            op.execute(statement)
    op.execute("INSERT INTO complaint_predictions (complaint_id, status, attempts, next_attempt_at) SELECT id, 'pending', 0, 0 FROM complaints WHERE kind = 'complaint'")


def downgrade():
    op.drop_table("complaint_predictions")
