"""Retry-safe Postgres -> Mongo projection. Run alongside the API.

Commit delivery markers only after idempotent Mongo upserts succeed. A crash can
replay an event, never duplicate it or lose a committed civic mutation.
"""

import argparse
import logging
import time
from datetime import UTC, datetime

from sqlalchemy import select

from app.db.mongo import ensure_indexes, mongo_database
from app.db.session import session_factory
from app.models.civic import OutboxEvent

logger = logging.getLogger(__name__)


def project_batch(db, mongo):
    rows = db.scalars(
        select(OutboxEvent)
        .where(OutboxEvent.delivered_at.is_(None))
        .order_by(OutboxEvent.created_at, OutboxEvent.id)
        .limit(100)
        .with_for_update(skip_locked=True)
    ).all()
    for row in rows:
        doc = {
            "event_type": row.event_type,
            "aggregate_id": row.aggregate_id,
            "payload": row.payload,
            "created_at": datetime.fromtimestamp(row.created_at, UTC),
        }
        mongo.civic_events.update_one({"_id": row.id}, {"$setOnInsert": doc}, upsert=True)
        if row.event_type == "complaint.created":
            mongo.road_observations.update_one(
                {"_id": row.id},
                {
                    "$setOnInsert": {
                        "complaint_id": row.aggregate_id,
                        **row.payload,
                        "observed_at": doc["created_at"],
                    }
                },
                upsert=True,
            )
        row.delivered_at = int(time.time())
    db.commit()
    return len(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    mongo = mongo_database()
    initialized = False
    while True:
        try:
            if not initialized:
                ensure_indexes(mongo)
                initialized = True
            with session_factory()() as db:
                count = project_batch(db, mongo)
            if args.once:
                print(f"Projected {count} events")
                return
            if count < 100:
                time.sleep(2)
        except Exception:
            if args.once:
                raise
            logger.exception("Event projection failed; committed events remain pending for retry")
            time.sleep(5)


if __name__ == "__main__":
    main()
