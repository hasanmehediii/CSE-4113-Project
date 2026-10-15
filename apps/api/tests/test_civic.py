import time
from unittest.mock import MagicMock

import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.core.rate_limit import LeakyBucket
from app.core.security import digest, hasher
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.civic import (
    Area,
    Category,
    Complaint,
    ComplaintPrediction,
    ModerationCase,
    OutboxEvent,
    PointEntry,
    Road,
    WorkerApplication,
    WorkerLocation,
)
from app.models.user import AuthSession, PasswordHistory, User
from app.services.auth_service import change_password
from app.services.catalog import CATEGORIES
from app.workers.bootstrap import bootstrap
from app.workers.classify_reports import Prediction, classify_batch
from app.workers.project_events import project_batch

ORIGIN = "http://localhost:3000"


@pytest.fixture
def civic_env(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    event.listen(
        engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON")
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as db:
        db.add_all(Category(code=c, label=l, base_priority=p) for c, l, p in CATEGORIES)
        db.commit()
    previous = app.state.limiter
    app.state.limiter = LeakyBucket(fakeredis.FakeRedis())
    monkeypatch.setattr(get_settings(), "media_directory", tmp_path)

    def test_db():
        with factory() as db:
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise

    app.dependency_overrides[get_db] = test_db
    with TestClient(app) as client:
        yield client, factory
    app.dependency_overrides.clear()
    app.state.limiter = previous
    engine.dispose()


def headers(client):
    return {"Origin": ORIGIN, "X-CSRF-Token": client.get("/api/v1/auth/csrf").json()["csrf_token"]}


def account(factory, name, role="citizen", verified=True):
    with factory() as db:
        user = User(name=name, email=f"{name}@example.com", role=role, email_verified=verified)
        db.add(user)
        db.flush()
        if role == "worker":
            db.add(WorkerApplication(user_id=user.id, nid_digest=digest(name), status="approved"))
        db.commit()
        return user.id


def sign_in(client, factory, user_id):
    token = f"session-token-for-{user_id}"
    with factory() as db:
        session = db.scalar(select(AuthSession).where(AuthSession.token_hash == digest(token)))
        if not session:
            db.add(
                AuthSession(
                    user_id=user_id,
                    token_hash=digest(token),
                    created_at=int(time.time()),
                    last_seen_at=int(time.time()),
                    expires_at=int(time.time()) + 3600,
                )
            )
            db.commit()
    client.cookies.set("session", token)


def payload(**overrides):
    return {
        "title": "Water overflowing on Road 12",
        "description": "Water is overflowing across this road.",
        "address": "Dhanmondi Road 12",
        "latitude": 23.751,
        "longitude": 90.375,
        "category_code": "road_flooding",
        **overrides,
    }


def create_report(client, **overrides):
    response = client.post("/api/v1/complaints", headers=headers(client), json=payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_public_reads_private_mutations_and_points(civic_env):
    client, factory = civic_env
    assert len(client.get("/api/v1/categories").json()) == 8
    assert client.get("/api/v1/complaints").json() == []
    assert (
        client.post("/api/v1/complaints", headers=headers(client), json=payload()).status_code
        == 401
    )
    user_id = account(factory, "resident")
    sign_in(client, factory, user_id)
    complaint_id = create_report(client)
    assert client.get("/api/v1/me/points").json()["balance"] == 1
    assert (
        client.put(
            f"/api/v1/complaints/{complaint_id}/vote", headers=headers(client), json={"value": 1}
        ).status_code
        == 403
    )
    client.cookies.clear()
    report = client.get(f"/api/v1/complaints/{complaint_id}").json()
    assert "email" not in report and "phone" not in report and "date_of_birth" not in report
    assert client.get("/api/v1/admin/users").status_code == 401


def test_pending_worker_cannot_self_approve_or_use_worker_routes(civic_env):
    client, factory = civic_env
    applicant = account(factory, "applicant")
    sign_in(client, factory, applicant)
    response = client.post(
        "/api/v1/workers/application", headers=headers(client), json={"nid_number": "1234567890"}
    )
    assert response.status_code == 202
    assert client.get("/api/v1/auth/me").json()["role"] == "citizen"
    assert (
        client.put(
            "/api/v1/workers/location",
            headers=headers(client),
            json={"latitude": 23.75, "longitude": 90.37},
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/admin/worker-applications/{applicant}/review",
            headers=headers(client),
            json={"approve": True, "note": "Looks good"},
        ).status_code
        == 403
    )
    with factory() as db:
        saved = db.get(WorkerApplication, applicant)
        assert saved.nid_digest != "1234567890" and len(saved.nid_digest) == 64
    mayor = account(factory, "mayor", "admin")
    sign_in(client, factory, mayor)
    approved = client.post(
        f"/api/v1/admin/worker-applications/{applicant}/review",
        headers=headers(client),
        json={"approve": True, "note": "Verified identity"},
    )
    assert approved.status_code == 200
    assert (
        client.post(
            f"/api/v1/admin/worker-applications/{applicant}/review",
            headers=headers(client),
            json={"approve": True, "note": "Again"},
        ).status_code
        == 409
    )
    sign_in(client, factory, applicant)
    assert client.get("/api/v1/auth/me").json()["role"] == "worker"


def test_false_threshold_requires_distinct_citizens_and_two_workers(civic_env):
    client, factory = civic_env
    author = account(factory, "author")
    sign_in(client, factory, author)
    create_report(client, title="Another legitimate report")
    target = create_report(client)
    for i in range(5):
        citizen = account(factory, f"voter{i}")
        sign_in(client, factory, citizen)
        for _ in range(2):
            result = client.put(
                f"/api/v1/complaints/{target}/vote", headers=headers(client), json={"value": -1}
            )
            assert result.status_code == 200, result.text
        assert result.json()["dislikes"] == i + 1
    for i in range(2):
        worker = account(factory, f"worker{i}", "worker")
        sign_in(client, factory, worker)
        result = client.post(
            f"/api/v1/complaints/{target}/false-reports",
            headers=headers(client),
            json={
                "comment": "The submitted claim is false",
                "image_url": "https://example.com/evidence.jpg",
            },
        )
        assert result.status_code == 201, result.text
        if i == 0:
            with factory() as db:
                assert db.get(Complaint, target).status == "open"
    with factory() as db:
        assert db.get(Complaint, target).status == "false"
        assert (
            db.scalar(select(func.sum(PointEntry.delta)).where(PointEntry.user_id == author)) == 0
        )
        assert db.scalar(select(func.count()).select_from(ModerationCase)) == 1
        assert db.get(User, author).is_active  # Only an administrator can block.


def assigned_report(client, factory):
    author = account(factory, "author")
    sign_in(client, factory, author)
    target = create_report(client)
    worker = account(factory, "cleaner", "worker")
    other = account(factory, "otherworker", "worker")
    mayor = account(factory, "mayor", "admin")
    sign_in(client, factory, mayor)
    result = client.post(
        f"/api/v1/admin/complaints/{target}/assign",
        headers=headers(client),
        json={"worker_id": worker},
    )
    assert result.status_code == 201, result.text
    assert (
        client.post(
            f"/api/v1/admin/complaints/{target}/assign",
            headers=headers(client),
            json={"worker_id": other},
        ).status_code
        == 409
    )
    sign_in(client, factory, other)
    assert (
        client.post(
            f"/api/v1/complaints/{target}/resolutions",
            headers=headers(client),
            json={"comment": "Claiming someone else's work"},
        ).status_code
        == 403
    )
    sign_in(client, factory, worker)
    result = client.post(
        f"/api/v1/complaints/{target}/resolutions",
        headers=headers(client),
        json={"comment": "We cleaned Dhanmondi Road 12"},
    )
    assert result.status_code == 201, result.text
    return target, worker, result.json()["id"]


def test_resolution_confirmation_five_votes_and_one_award(civic_env):
    client, factory = civic_env
    target, worker, resolution = assigned_report(client, factory)
    for i in range(5):
        citizen = account(factory, f"confirm{i}")
        sign_in(client, factory, citizen)
        for _ in range(2):
            result = client.put(
                f"/api/v1/resolutions/{resolution}/vote", headers=headers(client), json={"value": 1}
            )
            assert result.status_code == 200, result.text
        assert result.json()["status"] == ("pending" if i < 4 else "confirmed")
    with factory() as db:
        assert db.get(Complaint, target).status == "resolved"
        assert (
            db.scalar(select(func.sum(PointEntry.delta)).where(PointEntry.user_id == worker)) == 5
        )
        assert (
            db.scalar(
                select(func.count()).select_from(PointEntry).where(PointEntry.user_id == worker)
            )
            == 1
        )


def test_evidenced_worker_dispute_goes_to_admin(civic_env):
    client, factory = civic_env
    target, worker, resolution = assigned_report(client, factory)
    citizen = account(factory, "skeptic")
    sign_in(client, factory, citizen)
    url = f"/api/v1/resolutions/{resolution}/vote"
    assert client.put(url, headers=headers(client), json={"value": -1}).status_code == 422
    result = client.put(
        url,
        headers=headers(client),
        json={"value": -1, "image_url": "https://example.com/still-flooded.jpg"},
    )
    assert result.status_code == 200, result.text
    with factory() as db:
        assert db.get(Complaint, target).status == "disputed"
        case = db.scalar(select(ModerationCase))
        assert case.kind == "worker_dispute" and case.subject_user_id == worker
    assert (
        client.put(
            url,
            headers=headers(client),
            json={"value": -1, "image_url": "https://example.com/again.jpg"},
        ).status_code
        == 409
    )


def test_block_revokes_sessions_and_admin_analytics(civic_env):
    client, factory = civic_env
    user = account(factory, "member")
    sign_in(client, factory, user)
    create_report(client)
    mayor = account(factory, "mayor", "admin")
    sign_in(client, factory, mayor)
    analytics = client.get("/api/v1/admin/analytics")
    assert analytics.status_code == 200, analytics.text
    assert analytics.json()["by_status"] == {"open": 1}
    assert (
        client.patch(
            f"/api/v1/admin/users/{mayor}/block",
            headers=headers(client),
            json={"blocked": True, "reason": "Trying self block"},
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/v1/admin/users/{user}/block",
            headers=headers(client),
            json={"blocked": True, "reason": "Confirmed policy violation"},
        ).status_code
        == 200
    )
    sign_in(client, factory, user)
    assert client.get("/api/v1/auth/me").status_code == 401


def test_geographic_search_and_unknown_road_condition(civic_env):
    client, factory = civic_env
    with factory() as db:
        area = Area(name="Dhanmondi")
        db.add(area)
        db.flush()
        road = Road(name="Road 12", area_id=area.id, latitude=23.751, longitude=90.375)
        db.add(road)
        db.commit()
        road_id = road.id
    assert client.get("/api/v1/map/roads").json()[0]["condition"] == "unknown"
    user = account(factory, "reporter")
    sign_in(client, factory, user)
    create_report(client, road_id=road_id, kind="road_update", condition="good")
    assert client.get("/api/v1/map/roads").json()[0]["condition"] == "good"
    create_report(client, road_id=road_id)
    assert client.get("/api/v1/map/roads").json()[0]["condition"] == "bad"
    assert (
        len(client.get("/api/v1/complaints?latitude=23.75&longitude=90.375&radius_km=1").json())
        == 2
    )
    assert client.get("/api/v1/complaints?latitude=23.9&longitude=90.55&radius_km=1").json() == []
    assert client.get("/api/v1/map/hotspots").json()[0]["count"] == 1


def test_password_history_four_previous_and_reuse_rejected(civic_env):
    _, factory = civic_env
    user_id = account(factory, "history")
    with factory() as db:
        user = db.get(User, user_id)
        user.password_hash = hasher.hash("long-password-number-0")
        for i in range(1, 7):
            change_password(db, user, f"long-password-number-{i}")
            db.flush()
        db.commit()
        assert db.scalar(select(func.count()).select_from(PasswordHistory)) == 4
        with pytest.raises(Exception, match="recently used"):
            change_password(db, user, "long-password-number-5")


def test_projection_replay_is_idempotent(civic_env):
    client, factory = civic_env
    user_id = account(factory, "projection")
    sign_in(client, factory, user_id)
    create_report(client)
    mongo = MagicMock()
    with factory() as db:
        assert project_batch(db, mongo) == 1
        assert project_batch(db, mongo) == 0
        row = db.scalar(select(OutboxEvent))
        row.delivered_at = None
        db.commit()
        assert project_batch(db, mongo) == 1
    calls = mongo.civic_events.update_one.call_args_list
    assert calls[0].args[0] == calls[1].args[0]
    assert "$setOnInsert" in calls[0].args[1]


def test_auto_assign_ignores_stale_and_unavailable_workers(civic_env):
    client, factory = civic_env
    author = account(factory, "author")
    sign_in(client, factory, author)
    target = create_report(client)
    mayor = account(factory, "mayor", "admin")
    stale = account(factory, "stale", "worker")
    ready = account(factory, "ready", "worker")
    with factory() as db:
        db.add(
            WorkerLocation(
                user_id=stale, latitude=23.751, longitude=90.375, updated_at=int(time.time()) - 1000
            )
        )
        db.add(
            WorkerLocation(
                user_id=ready, latitude=23.76, longitude=90.38, updated_at=int(time.time())
            )
        )
        db.commit()
    sign_in(client, factory, mayor)
    result = client.post(
        f"/api/v1/admin/complaints/{target}/assign", headers=headers(client), json={}
    )
    assert result.status_code == 201 and result.json()["worker_id"] == ready


def test_upload_is_authenticated_and_rejects_active_content(civic_env):
    client, factory = civic_env
    user_id = account(factory, "photographer")
    sign_in(client, factory, user_id)
    assert (
        client.post(
            "/api/v1/media",
            headers=headers(client),
            files={"file": ("x.svg", b"<svg></svg>", "image/svg+xml")},
        ).status_code
        == 422
    )
    uploaded = client.post(
        "/api/v1/media",
        headers=headers(client),
        files={"file": ("photo.png", b"\x89PNG\r\n\x1a\nTEST", "image/png")},
    )
    assert uploaded.status_code == 201
    target = create_report(client, images=[uploaded.json()["url"]])
    assert client.get(f"/api/v1/complaints/{target}").json()["images"] == [uploaded.json()["url"]]


def test_bootstrap_never_promotes_existing_citizen(civic_env):
    _, factory = civic_env
    user_id = account(factory, "already")
    settings = Settings(
        _env_file=None, admin_email="already@example.com", admin_password="a-long-admin-password"
    )
    with factory() as db:
        with pytest.raises(ValueError, match="privilege escalation"):
            bootstrap(db, settings)
        assert db.get(User, user_id).role == "citizen"


def test_classifier_failure_retries_and_success_keeps_original_category(civic_env):
    client, factory = civic_env
    author = account(factory, "classified")
    sign_in(client, factory, author)
    target = create_report(client)

    def unavailable(_):
        raise OSError("ML service unavailable")

    with factory() as db:
        assert classify_batch(db, unavailable) == 1
        job = db.get(ComplaintPrediction, target)
        assert (
            job.status == "pending" and job.attempts == 1 and job.next_attempt_at > int(time.time())
        )
        job.next_attempt_at = 0
        db.commit()
        assert (
            classify_batch(
                db,
                lambda _: Prediction(
                    predicted_category="open_manhole", confidence=0.9, model_version="test-model"
                ),
            )
            == 1
        )
        assert db.get(Complaint, target).category_code == "road_flooding"
    row = client.get(f"/api/v1/complaints/{target}").json()
    assert row["priority"] == 95 and row["priority_source"] == "ml_category_rules"
    assert row["classification"]["model_version"] == "test-model"


def test_admin_can_dismiss_worker_dispute_once(civic_env):
    client, factory = civic_env
    target, _worker, resolution = assigned_report(client, factory)
    citizen = account(factory, "disputer")
    sign_in(client, factory, citizen)
    result = client.put(
        f"/api/v1/resolutions/{resolution}/vote",
        headers=headers(client),
        json={"value": -1, "image_url": "https://example.com/dispute.jpg"},
    )
    assert result.status_code == 200
    with factory() as db:
        case_id = db.scalar(select(ModerationCase.id))
        mayor_id = db.scalar(select(User.id).where(User.role == "admin"))
    sign_in(client, factory, mayor_id)
    url = f"/api/v1/admin/moderation/{case_id}/review"
    assert (
        client.post(
            url,
            headers=headers(client),
            json={"status": "dismissed", "note": "Evidence does not match this location"},
        ).status_code
        == 200
    )
    assert client.get(f"/api/v1/complaints/{target}").json()["status"] == "awaiting_confirmation"
    assert (
        client.post(
            url, headers=headers(client), json={"status": "dismissed", "note": "Repeated request"}
        ).status_code
        == 409
    )
    sign_in(client, factory, citizen)
    assert (
        client.put(
            f"/api/v1/resolutions/{resolution}/vote",
            headers=headers(client),
            json={"value": -1, "image_url": "https://example.com/dispute.jpg"},
        ).status_code
        == 409
    )


def test_worker_can_stop_availability_without_new_location(civic_env):
    client, factory = civic_env
    worker = account(factory, "availableworker", "worker")
    sign_in(client, factory, worker)
    assert (
        client.patch(
            "/api/v1/workers/availability", headers=headers(client), json={"available": False}
        ).status_code
        == 200
    )
    assert (
        client.patch(
            "/api/v1/workers/availability", headers=headers(client), json={"available": True}
        ).status_code
        == 409
    )
