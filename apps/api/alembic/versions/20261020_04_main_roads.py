"""Seed the initial Dhaka main-road selection catalog."""
from alembic import op
from sqlalchemy.orm import Session

from app.services.road_catalog import seed_main_roads

revision = "20261020_04"
down_revision = "20261015_03"
branch_labels = None
depends_on = None


def upgrade():
    with Session(bind=op.get_bind()) as db:
        seed_main_roads(db)


def downgrade():
    # Preserve catalog rows: resident reports may already reference them.
    pass
