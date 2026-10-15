"""Use the existing ML service; category urgency remains an explicit policy.

Failed calls retain pending jobs with exponential backoff. Model output never
overwrites the citizen's selected category or changes complaint truth/status.
"""

import argparse
import json
import logging
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import session_factory
from app.models.civic import Category, Complaint, ComplaintPrediction, now

logger = logging.getLogger(__name__)


class Prediction(BaseModel):
    predicted_category: str = Field(max_length=40)
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    model_version: str = Field(min_length=1, max_length=100)


def predict(text):
    request = Request(
        get_settings().ml_service_url.rstrip("/") + "/classify",
        data=json.dumps({"text": text}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        return Prediction.model_validate_json(response.read(32768))


def classify_batch(db, predictor=predict):
    jobs = db.scalars(
        select(ComplaintPrediction)
        .where(
            ComplaintPrediction.status == "pending", ComplaintPrediction.next_attempt_at <= now()
        )
        .order_by(ComplaintPrediction.next_attempt_at)
        .limit(5)
        .with_for_update(skip_locked=True)
    ).all()
    for job in jobs:
        job.attempts += 1
        row = db.get(Complaint, job.complaint_id)
        try:
            result = predictor(row.description)
            if not db.get(Category, result.predicted_category):
                raise ValueError("Unrecognised model category")
            job.predicted_category, job.confidence, job.model_version = (
                result.predicted_category,
                result.confidence,
                result.model_version,
            )
            job.status, job.classified_at = "ready", now()
        except (OSError, URLError, ValueError, ValidationError):
            job.next_attempt_at = now() + min(3600, 5 * 2 ** min(job.attempts, 10))
            logger.warning(
                "Classification unavailable for complaint %s; retaining category fallback", row.id
            )
    db.commit()
    return len(jobs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    while True:
        try:
            with session_factory()() as db:
                count = classify_batch(db)
            if args.once:
                print(f"Processed {count} classification jobs")
                return
        except Exception:
            if args.once:
                raise
            logger.exception("Classification worker failed; retrying")
        time.sleep(5)


if __name__ == "__main__":
    main()
