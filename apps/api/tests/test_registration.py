import pytest
import test_auth
from sqlalchemy import func, select
from test_auth import csrf

from app.models.civic import WorkerApplication
from app.models.user import User


@pytest.fixture
def registration_env(monkeypatch):
    yield from test_auth.auth_env.__wrapped__(monkeypatch)


def signup_payload(**overrides):
    return {
        "name": "New Resident",
        "email": "signup@example.com",
        "password": "a-long-signup-passphrase",
        "account_type": "citizen",
        **overrides,
    }


def test_citizen_signup_saves_profile_without_worker_application(registration_env):
    client, factory, sent, _ = registration_env
    result = client.post(
        "/api/v1/auth/register",
        headers=csrf(client),
        json=signup_payload(phone="01712345678", date_of_birth="2000-01-02", blood_group="B+"),
    )
    assert result.status_code == 202, result.text
    with factory() as db:
        user = db.scalar(select(User))
        assert user.role == "citizen" and user.phone == "+8801712345678"
        assert str(user.date_of_birth) == "2000-01-02" and user.blood_group == "B+"
        assert db.get(WorkerApplication, user.id) is None
    assert len(sent) == 1 and sent[0][2] == "verify"


def test_worker_signup_queues_identity_and_never_grants_worker_access(registration_env):
    client, factory, sent, _ = registration_env
    result = client.post(
        "/api/v1/auth/register",
        headers=csrf(client),
        json=signup_payload(account_type="worker", worker_identity={"nid_number": "1234567890"}),
    )
    assert result.status_code == 202, result.text
    with factory() as db:
        user = db.scalar(select(User))
        application = db.get(WorkerApplication, user.id)
        assert user.role == "citizen" and application.status == "pending"
        assert len(application.nid_digest) == 64 and application.nid_digest != "1234567890"
    assert (
        client.post(
            "/api/v1/auth/verify-email", headers=csrf(client), json={"token": sent[-1][1]}
        ).status_code
        == 200
    )
    login = client.post(
        "/api/v1/auth/login",
        headers=csrf(client),
        json={"identifier": "signup@example.com", "password": "a-long-signup-passphrase"},
    )
    assert login.status_code == 200
    assert (
        login.json()["role"] == "citizen" and login.json()["worker_application_status"] == "pending"
    )
    assert client.get("/api/v1/auth/me").json()["worker_application_status"] == "pending"
    assert client.get("/api/v1/workers/application").json()["status"] == "pending"
    assert client.get("/api/v1/workers/assignments").status_code == 403


@pytest.mark.parametrize(
    "extra",
    [
        {"account_type": "worker"},
        {"account_type": "worker", "worker_identity": {}},
        {"account_type": "worker", "worker_identity": {"nid_number": "123"}},
        {"account_type": "admin"},
        {"role": "admin"},
        {"worker_identity": {"nid_number": "1234567890"}},
    ],
)
def test_registration_rejects_missing_identity_and_privilege_injection(registration_env, extra):
    client, factory, sent, _ = registration_env
    result = client.post(
        "/api/v1/auth/register", headers=csrf(client), json=signup_payload(**extra)
    )
    assert result.status_code == 422, result.text
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 0
    assert not sent


def test_nid_conflict_rolls_back_the_whole_worker_registration(registration_env):
    client, factory, sent, _ = registration_env
    data = signup_payload(account_type="worker", worker_identity={"nid_number": "1234567890"})
    first = client.post("/api/v1/auth/register", headers=csrf(client), json=data)
    data["email"] = "another-worker@example.com"
    second = client.post("/api/v1/auth/register", headers=csrf(client), json=data)
    assert first.status_code == second.status_code == 202
    assert first.json() == second.json()  # Do not disclose another person's identity registration.
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 1
        assert db.scalar(select(func.count()).select_from(WorkerApplication)) == 1
    assert len(sent) == 1
