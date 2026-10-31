"""Shared identity submission for worker signup and existing citizens applying later."""

import hashlib
import hmac

from app.core.config import get_settings
from app.models.civic import WorkerApplication, now
from app.services.civic_service import event


def submit_application(db, user_id, identity, existing=None):
    # Caller holds the account lock or is creating the account in this transaction.
    fingerprint = (
        hmac.new(
            get_settings().auth_secret.encode(), identity.nid_number.encode(), hashlib.sha256
        ).hexdigest()
        if identity.nid_number
        else None
    )
    row = existing or WorkerApplication(user_id=user_id)
    row.nid_digest, row.nid_image_url = fingerprint, identity.nid_image_url
    row.status, row.submitted_at = "pending", now()
    row.reviewed_at, row.reviewed_by, row.review_note = None, None, None
    db.add(row)
    db.flush()
    event(db, "worker.applied", user_id)
    return row
