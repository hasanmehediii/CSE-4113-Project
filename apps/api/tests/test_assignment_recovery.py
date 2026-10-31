"""Recover assigned work without losing history or accepting stale completions."""
import pytest
import test_civic
from sqlalchemy import select

from app.models.civic import Assignment, Complaint, WorkerLocation


@pytest.fixture
def recovery_env(tmp_path, monkeypatch):
    yield from test_civic.civic_env.__wrapped__(tmp_path, monkeypatch)


def assignment_env(client, factory):
    author = test_civic.account(factory, "recovery-author")
    old = test_civic.account(factory, "recovery-old", "worker")
    new = test_civic.account(factory, "recovery-new", "worker")
    mayor = test_civic.account(factory, "recovery-mayor", "admin")
    test_civic.sign_in(client, factory, author)
    report = test_civic.create_report(client)
    test_civic.sign_in(client, factory, mayor)
    url = f"/api/v1/admin/complaints/{report}/assign"
    response = client.post(url, headers=test_civic.headers(client), json={"worker_id": old})
    assert response.status_code == 201
    return report, old, new, mayor, url


@pytest.mark.parametrize("block_old", [False, True])
def test_reassignment_recovers_blocked_or_unavailable_worker(recovery_env, block_old):
    client, factory = recovery_env
    report, old, new, _mayor, url = assignment_env(client, factory)
    if block_old:
        assert client.patch(
            f"/api/v1/admin/users/{old}/block", headers=test_civic.headers(client),
            json={"blocked": True, "reason": "Worker no longer available"},
        ).status_code == 200
    response = client.post(
        url, headers=test_civic.headers(client), json={"worker_id": new, "reassign": True}
    )
    assert response.status_code == 201, response.text
    with factory() as db:
        rows = db.scalars(select(Assignment).where(Assignment.complaint_id == report)).all()
        assert {(row.worker_id, row.status) for row in rows} == {
            (old, "cancelled"), (new, "active")
        }
    test_civic.sign_in(client, factory, old)
    assert client.post(
        f"/api/v1/complaints/{report}/resolutions", headers=test_civic.headers(client),
        json={"comment": "Stale completion from the previous worker"},
    ).status_code == (401 if block_old else 403)
    test_civic.sign_in(client, factory, new)
    assert client.post(
        f"/api/v1/complaints/{report}/resolutions", headers=test_civic.headers(client),
        json={"comment": "The replacement worker has completed the work"},
    ).status_code == 201


@pytest.mark.parametrize("replacement", ["same", "citizen", "no_available_worker"])
def test_failed_reassignment_keeps_current_worker(recovery_env, replacement):
    client, factory = recovery_env
    report, old, _new, _mayor, url = assignment_env(client, factory)
    worker_id = old if replacement == "same" else (
        test_civic.account(factory, "not-a-worker") if replacement == "citizen" else None
    )
    response = client.post(
        url, headers=test_civic.headers(client), json={"worker_id": worker_id, "reassign": True}
    )
    assert response.status_code == (422 if replacement == "citizen" else 409)
    with factory() as db:
        rows = db.scalars(select(Assignment).where(Assignment.complaint_id == report)).all()
        assert [(row.worker_id, row.status) for row in rows] == [(old, "active")]


def test_automatic_reassignment_excludes_current_worker(recovery_env):
    client, factory = recovery_env
    report, old, new, _mayor, url = assignment_env(client, factory)
    with factory() as db:
        db.add_all(WorkerLocation(user_id=worker, latitude=23.751, longitude=90.375)
                   for worker in (old, new))
        db.commit()
    response = client.post(url, headers=test_civic.headers(client), json={"reassign": True})
    assert response.status_code == 201, response.text
    assert response.json()["worker_id"] == new
    assert client.get(f"/api/v1/complaints/{report}").json()["status"] == "assigned"


def test_active_work_is_paginated_separately_from_completed_history(recovery_env):
    client, factory = recovery_env
    author = test_civic.account(factory, "backlog-author")
    worker = test_civic.account(factory, "backlog-worker", "worker")
    other = test_civic.account(factory, "backlog-other", "worker")
    with factory() as db:
        for index in range(38):
            complaint = Complaint(author_id=author, **test_civic.payload(), status="assigned")
            db.add(complaint)
            db.flush()
            db.add(Assignment(
                complaint_id=complaint.id, worker_id=other if index == 37 else worker,
                source="admin", status="active" if index < 35 or index == 37 else "completed",
                created_at=index,
            ))
        db.commit()
    test_civic.sign_in(client, factory, worker)
    first = client.get("/api/v1/workers/assignments?status=active&limit=30").json()
    second = client.get("/api/v1/workers/assignments?status=active&limit=30&offset=30").json()
    assert len(first) == 30 and len(second) == 5
    assert len({row["id"] for row in first + second}) == 35
    assert all(row["status"] == "active" for row in first + second)
    assert len(client.get("/api/v1/workers/assignments?status=completed").json()) == 2
