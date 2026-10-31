"""Moderation and historical completions cannot overwrite the current work cycle."""
import pytest
import test_civic as civic
from sqlalchemy import func, select

from app.models.civic import (
    Assignment,
    Complaint,
    ModerationCase,
    PointEntry,
    Resolution,
    ResolutionVote,
)
from app.models.user import User


@pytest.fixture
def lifecycle_env(tmp_path, monkeypatch):
    yield from civic.civic_env.__wrapped__(tmp_path, monkeypatch)


def vote(client, factory, resolution, name, value=1):
    voter = civic.account(factory, name)
    civic.sign_in(client, factory, voter)
    result = client.put(f"/api/v1/resolutions/{resolution}/vote", headers=civic.headers(client),
                        json={"value": value, **({"image_url": "https://example.com/dispute.png"} if value < 0 else {})})
    assert result.status_code == 200, result.text
    return result.json()


def mark_false(client, factory, complaint):
    for index in range(5):
        voter = civic.account(factory, f"false-voter-{index}")
        civic.sign_in(client, factory, voter)
        assert client.put(f"/api/v1/complaints/{complaint}/vote", headers=civic.headers(client),
                          json={"value": -1}).status_code == 200
    for index in range(2):
        worker = civic.account(factory, f"false-inspector-{index}", "worker")
        civic.sign_in(client, factory, worker)
        assert client.post(f"/api/v1/complaints/{complaint}/false-reports", headers=civic.headers(client),
                           json={"comment": "Evidence from an independent inspection",
                                 "image_url": "https://example.com/inspection.png"}).status_code == 201
    with factory() as db:
        assert db.get(Complaint, complaint).status == "false"
        return db.scalar(select(ModerationCase.id).where(ModerationCase.kind == "false_complaint"))


def mayor(client, factory):
    with factory() as db:
        admin = db.scalar(select(User.id).where(User.role == "admin"))
    civic.sign_in(client, factory, admin)


def review(client, case):
    return client.post(f"/api/v1/admin/moderation/{case}/review", headers=civic.headers(client),
                       json={"status": "dismissed", "note": "Independent inspection disproves the allegation"})


def test_false_case_dismissal_restores_pending_completion_and_blocks_another_assignment(lifecycle_env):
    client, factory = lifecycle_env
    complaint, worker, resolution = civic.assigned_report(client, factory)
    for index in range(4):
        vote(client, factory, resolution, f"approval-{index}")
    witness = civic.account(factory, "later-witness")
    civic.sign_in(client, factory, witness)
    child = civic.create_report(client)
    case = mark_false(client, factory, complaint)
    mayor(client, factory)
    assert review(client, case).status_code == 200
    for report in (complaint, child):
        assert client.get(f"/api/v1/complaints/{report}").json()["status"] == "awaiting_confirmation"
    replacement = civic.account(factory, "replacement", "worker")
    assert client.post(f"/api/v1/admin/complaints/{child}/assign", headers=civic.headers(client),
                       json={"worker_id": replacement}).status_code == 409
    vote(client, factory, resolution, "fifth-approval")
    with factory() as db:
        assert db.get(Complaint, complaint).status == db.get(Complaint, child).status == "resolved"
        assert db.scalar(select(func.count()).select_from(Assignment).where(Assignment.status == "active")) == 0
        assert db.scalar(select(func.sum(PointEntry.delta)).where(PointEntry.user_id == worker)) == 5


@pytest.mark.parametrize("state", ["confirmed", "disputed"])
def test_false_case_dismissal_restores_confirmed_or_disputed_completion(lifecycle_env, state):
    client, factory = lifecycle_env
    complaint, _, resolution = civic.assigned_report(client, factory)
    if state == "confirmed":
        for index in range(5):
            vote(client, factory, resolution, f"confirmed-{index}")
    else:
        vote(client, factory, resolution, "disputed-voter", -1)
    case = mark_false(client, factory, complaint)
    mayor(client, factory)
    assert review(client, case).status_code == 200
    assert client.get(f"/api/v1/complaints/{complaint}").json()["status"] == (
        "resolved" if state == "confirmed" else "disputed"
    )


def test_old_completion_votes_cannot_resolve_or_dispute_replacement_work(lifecycle_env):
    client, factory = lifecycle_env
    complaint, original_worker, old = civic.assigned_report(client, factory)
    for index in range(4):
        vote(client, factory, old, f"old-approval-{index}")
    case = mark_false(client, factory, complaint)
    mayor(client, factory)
    assert review(client, case).status_code == 200
    # Reproduce an already-open incident left by the previous dismissal behavior.
    with factory() as db:
        db.get(Complaint, complaint).status = "open"
        db.commit()
    replacement = civic.account(factory, "replacement-worker", "worker")
    assert client.post(f"/api/v1/admin/complaints/{complaint}/assign", headers=civic.headers(client),
                       json={"worker_id": replacement}).status_code == 201
    voter = civic.account(factory, "late-old-voter")

    def reject_old():
        civic.sign_in(client, factory, voter)
        for value in (1, -1):
            response = client.put(f"/api/v1/resolutions/{old}/vote", headers=civic.headers(client), json={
                "value": value, "image_url": "https://example.com/late.png",
            })
            assert response.status_code == 409, response.text

    reject_old()
    assert client.get(f"/api/v1/complaints/{complaint}").json()["status"] == "assigned"
    civic.sign_in(client, factory, replacement)
    completed = client.post(f"/api/v1/complaints/{complaint}/resolutions", headers=civic.headers(client),
                            json={"comment": "Replacement independently cleared the road"})
    assert completed.status_code == 201, completed.text
    current = completed.json()["id"]
    # Supersession is explicit, so even equal timestamps cannot make the old
    # completion current after the replacement has submitted its own evidence.
    with factory() as db:
        db.get(Resolution, current).created_at = db.get(Resolution, old).created_at
        db.commit()
    reject_old()
    for index in range(5):
        vote(client, factory, current, f"new-approval-{index}")
    reject_old()
    with factory() as db:
        assert db.get(Complaint, complaint).status == "resolved"
        assert db.get(Resolution, old).status == "pending"
        assert db.scalar(select(func.count()).select_from(ResolutionVote).where(ResolutionVote.resolution_id == old)) == 4
        assert db.scalar(select(func.coalesce(func.sum(PointEntry.delta), 0)).where(PointEntry.user_id == original_worker)) == 0
        assert db.scalar(select(func.sum(PointEntry.delta)).where(PointEntry.user_id == replacement)) == 5


def test_old_dispute_dismissal_cannot_restore_a_different_disputed_completion(lifecycle_env):
    client, factory = lifecycle_env
    complaint, _, old = civic.assigned_report(client, factory)
    vote(client, factory, old, "old-disputer", -1)
    with factory() as db:
        old_case = db.scalar(select(ModerationCase.id).where(ModerationCase.resolution_id == old))
    replacement = civic.account(factory, "new-disputed-worker", "worker")
    mayor(client, factory)
    assert client.post(f"/api/v1/admin/complaints/{complaint}/assign", headers=civic.headers(client),
                       json={"worker_id": replacement}).status_code == 201
    civic.sign_in(client, factory, replacement)
    result = client.post(f"/api/v1/complaints/{complaint}/resolutions", headers=civic.headers(client),
                         json={"comment": "Another work cycle completed"})
    current = result.json()["id"]
    vote(client, factory, current, "new-disputer", -1)
    mayor(client, factory)
    assert review(client, old_case).status_code == 409
    with factory() as db:
        assert db.get(Complaint, complaint).status == "disputed"
        assert db.get(Resolution, current).status == "disputed"
        assert db.get(ModerationCase, old_case).status == "open"


def test_false_dismissal_without_completion_reopens_but_does_not_reactivate_cancelled_work(lifecycle_env):
    client, factory = lifecycle_env
    complaint, _, resolution = civic.assigned_report(client, factory)
    # An assigned job which has never been completed is a different lifecycle.
    with factory() as db:
        completed = db.get(Resolution, resolution)
        assignment = db.get(Assignment, completed.assignment_id)
        db.delete(completed)
        assignment.status, assignment.completed_at = "active", None
        db.get(Complaint, complaint).status = "assigned"
        db.commit()
    case = mark_false(client, factory, complaint)
    mayor(client, factory)
    assert review(client, case).status_code == 200
    with factory() as db:
        assert db.get(Complaint, complaint).status == "open"
        assert db.scalar(select(Assignment.status).where(Assignment.complaint_id == complaint)) == "cancelled"


def test_false_dismissal_cannot_overwrite_work_that_has_already_moved_on(lifecycle_env):
    client, factory = lifecycle_env
    complaint, _, _ = civic.assigned_report(client, factory)
    case = mark_false(client, factory, complaint)
    # Guard against stale reviews of previously inconsistent legacy state.
    with factory() as db:
        db.get(Complaint, complaint).status = "open"
        db.commit()
    mayor(client, factory)
    replacement = civic.account(factory, "moved-on-worker", "worker")
    assert client.post(f"/api/v1/admin/complaints/{complaint}/assign", headers=civic.headers(client),
                       json={"worker_id": replacement}).status_code == 201
    assert review(client, case).status_code == 409
    with factory() as db:
        assert db.get(Complaint, complaint).status == "assigned"
        assert db.get(ModerationCase, case).status == "open"
