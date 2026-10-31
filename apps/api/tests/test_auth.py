import time

import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.rate_limit import LeakyBucket
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import AuthSession, User
from app.services.google_provider import get_google_provider

ORIGIN = "http://localhost:3000"


@pytest.fixture
def auth_env(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    redis = fakeredis.FakeRedis()
    old_limiter = app.state.limiter
    app.state.limiter = LeakyBucket(redis)
    sent = []
    monkeypatch.setattr(
        "app.api.v1.auth.send_action_email",
        lambda email, token, purpose: sent.append((email, token, purpose)),
    )

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
        yield client, factory, sent, redis
    app.dependency_overrides.clear()
    app.state.limiter = old_limiter
    engine.dispose()


def csrf(client):
    token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    return {"Origin": ORIGIN, "X-CSRF-Token": token}


def register_and_verify(client, sent, email="a@example.com"):
    response = client.post(
        "/api/v1/auth/register",
        headers=csrf(client),
        json={"email": email, "name": "Alice", "password": "very-long-passphrase-1"},
    )
    assert response.status_code == 202, response.text
    assert sent[-1][2] == "verify"
    response = client.post(
        "/api/v1/auth/verify-email", headers=csrf(client), json={"token": sent[-1][1]}
    )
    assert response.status_code == 200, response.text


def test_password_session_csrf_logout_and_replay(auth_env):
    client, factory, sent, _ = auth_env
    register_and_verify(client, sent)
    assert (
        client.post(
            "/api/v1/auth/verify-email", headers=csrf(client), json={"token": sent[-1][1]}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "a@example.com", "password": "very-long-passphrase-1"},
        ).status_code
        == 403
    )
    login = client.post(
        "/api/v1/auth/login",
        headers=csrf(client),
        json={"email": "a@example.com", "password": "very-long-passphrase-1"},
    )
    assert login.status_code == 200, login.text
    assert login.json()["email_verified"] is True
    assert "httponly" in login.headers["set-cookie"].lower()
    assert client.get("/api/v1/auth/me").json()["email"] == "a@example.com"
    assert len(client.get("/api/v1/auth/sessions").json()) == 1
    assert (
        client.post(
            "/api/v1/auth/logout",
            headers={
                "Origin": "https://evil.example",
                "X-CSRF-Token": csrf(client)["X-CSRF-Token"],
            },
        ).status_code
        == 403
    )
    assert client.post("/api/v1/auth/logout", headers=csrf(client)).status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401
    with factory() as db:
        assert db.scalar(select(AuthSession)).revoked


def test_password_reset_revokes_all_sessions(auth_env):
    client, _, sent, _ = auth_env
    register_and_verify(client, sent)
    client.post(
        "/api/v1/auth/login",
        headers=csrf(client),
        json={"email": "a@example.com", "password": "very-long-passphrase-1"},
    )
    assert (
        client.post(
            "/api/v1/auth/forgot-password", headers=csrf(client), json={"email": "a@example.com"}
        ).status_code
        == 202
    )
    reset = sent[-1][1]
    assert (
        client.post(
            "/api/v1/auth/reset-password",
            headers=csrf(client),
            json={"token": reset, "password": "different-long-password-2"},
        ).status_code
        == 200
    )
    assert client.get("/api/v1/auth/me").status_code == 401
    assert (
        client.post(
            "/api/v1/auth/reset-password",
            headers=csrf(client),
            json={"token": reset, "password": "different-long-password-3"},
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/auth/login",
            headers=csrf(client),
            json={"email": "a@example.com", "password": "very-long-passphrase-1"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/login",
            headers=csrf(client),
            json={"email": "a@example.com", "password": "different-long-password-2"},
        ).status_code
        == 200
    )


def test_idle_session_expires(auth_env):
    client, factory, sent, _ = auth_env
    register_and_verify(client, sent)
    client.post(
        "/api/v1/auth/login",
        headers=csrf(client),
        json={"email": "a@example.com", "password": "very-long-passphrase-1"},
    )
    with factory() as db:
        db.execute(update(AuthSession).values(last_seen_at=int(time.time()) - 4000))
        db.commit()
    assert client.get("/api/v1/auth/me").status_code == 401


def test_leaky_bucket_drains_and_rejects_without_queueing(auth_env):
    _, _, _, redis = auth_env
    limiter = LeakyBucket(redis)
    assert [limiter.consume("sample", 2, 4) for _ in range(3)] == [0, 0, 2]
    redis.hincrbyfloat("sample", "updated", -2)
    assert limiter.consume("sample", 2, 4) == 0


def test_login_rate_limit_returns_retry_after(auth_env):
    client, _, _, _ = auth_env
    headers = csrf(client)
    payload = {"email": "unknown@example.com", "password": "wrong-password"}
    for _ in range(5):
        assert client.post("/api/v1/auth/login", headers=headers, json=payload).status_code == 401
    blocked = client.post("/api/v1/auth/login", headers=headers, json=payload)
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0


def test_google_nonce_and_no_automatic_email_link(auth_env, monkeypatch):
    client, factory, sent, _ = auth_env
    register_and_verify(client, sent, "alice@gmail.com")
    monkeypatch.setattr(get_settings(), "google_client_id", "test-client")
    headers = csrf(client)
    nonce = client.post("/api/v1/auth/google/nonce", headers=headers).json()["nonce"]

    class Provider:
        def verify(self, credential):
            return {
                "sub": "google-123",
                "email": "alice@gmail.com",
                "email_verified": True,
                "name": "Alice",
                "nonce": nonce,
            }

    app.dependency_overrides[get_google_provider] = Provider
    response = client.post(
        "/api/v1/auth/google", headers=headers, json={"credential": "fake-id-token", "nonce": nonce}
    )
    assert response.status_code == 409
    with factory() as db:
        assert len(db.scalars(select(User)).all()) == 1


def test_google_creates_user_and_nonce_is_single_use(auth_env, monkeypatch):
    client, _, _, _ = auth_env
    monkeypatch.setattr(get_settings(), "google_client_id", "test-client")
    headers = csrf(client)
    nonce = client.post("/api/v1/auth/google/nonce", headers=headers).json()["nonce"]

    class Provider:
        def verify(self, credential):
            return {
                "sub": "google-456",
                "email": "new@gmail.com",
                "email_verified": True,
                "name": "New User",
                "nonce": nonce,
            }

    app.dependency_overrides[get_google_provider] = Provider
    payload = {"credential": "fake-id-token", "nonce": nonce}
    response = client.post("/api/v1/auth/google", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    assert client.get("/api/v1/auth/me").json()["email"] == "new@gmail.com"
    assert client.post("/api/v1/auth/google", headers=csrf(client), json=payload).status_code == 401
