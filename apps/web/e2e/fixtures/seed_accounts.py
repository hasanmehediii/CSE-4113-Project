"""Create or refresh the synthetic browser-test accounts in the ISOLATED e2e database.

Run by e2e/global-setup.ts through `docker compose exec -T api uv run --no-sync python -`
inside the dubsibhai-e2e project. Inputs come from environment variables:
E2E_ACCOUNTS (JSON list of {key, email, name, role}) and E2E_PASSWORD.
Prints {"key": "user id", ...} as JSON. Safe to run again: accounts are updated in place.
"""
import json
import os
import sys

from sqlalchemy import select

from app.core.security import hasher
from app.db.session import session_factory
from app.models.civic import WorkerApplication, now
from app.models.user import User

if os.environ.get("E2E_ISOLATED_STACK") != "1":
    sys.exit("Refusing to create test accounts: this is not the isolated e2e stack.")

accounts = json.loads(os.environ["E2E_ACCOUNTS"])
password = os.environ["E2E_PASSWORD"]
if any(not row["email"].endswith("@example.com") for row in accounts):
    sys.exit("Refusing to create test accounts: only synthetic @example.com addresses are allowed.")

with session_factory()() as db:
    users = {}
    for row in accounts:
        user = db.scalar(select(User).where(User.email == row["email"]))
        if user is None:
            user = User(email=row["email"])
            db.add(user)
        user.name, user.role = row["name"], row["role"]
        user.email_verified, user.is_active = True, True
        # A new random password each run; earlier runs' passwords stop working.
        user.password_hash = hasher.hash(password)
        db.flush()
        users[row["key"]] = user
    mayor = next(user for user in users.values() if user.role == "admin")
    for key, user in users.items():
        if user.role != "worker":
            continue
        # Equivalent to a mayor approving a worker application.
        application = db.get(WorkerApplication, user.id) or WorkerApplication(user_id=user.id)
        application.nid_image_url = "https://example.com/e2e-synthetic-nid.png"
        application.status = "approved"
        application.submitted_at = application.submitted_at or now()
        application.reviewed_at, application.reviewed_by = now(), mayor.id
        application.review_note = "Synthetic browser-test fixture"
        db.add(application)
    db.commit()
    print(json.dumps({key: user.id for key, user in users.items()}))
