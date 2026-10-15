from datetime import date

import pytest
import test_auth
from sqlalchemy import select
from test_auth import csrf, register_and_verify

from app.models.user import ActionToken, User
from app.services.auth_service import change_password


@pytest.fixture
def recovery_env(monkeypatch):
    yield from test_auth.auth_env.__wrapped__(monkeypatch)


def test_phone_login_normalizes_local_and_international_numbers(recovery_env):
    client, factory, sent, _ = recovery_env
    register_and_verify(client, sent)
    with factory() as db:
        db.scalar(select(User)).phone = "+8801712345678"
        db.commit()
    response = client.post(
        "/api/v1/auth/login",
        headers=csrf(client),
        json={"identifier": "01712345678", "password": "very-long-passphrase-1"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["phone"] == "+8801712345678"


def test_old_password_dob_requires_single_use_email_link(recovery_env):
    client, factory, sent, _ = recovery_env
    register_and_verify(client, sent)
    with factory() as db:
        user = db.scalar(select(User))
        user.date_of_birth = date(2000, 1, 2)
        change_password(db, user, "a-different-long-password")
        db.commit()
    result = client.post(
        "/api/v1/auth/recover",
        headers=csrf(client),
        json={
            "email": "a@example.com",
            "date_of_birth": "2000-01-02",
            "remembered_password": "very-long-passphrase-1",
        },
    )
    assert result.status_code == 202 and sent[-1][2] == "reset"
    assert client.get("/api/v1/auth/me").status_code == 401
    reset = sent[-1][1]
    assert (
        client.post(
            "/api/v1/auth/reset-password",
            headers=csrf(client),
            json={"token": reset, "password": "an-entirely-new-password"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/auth/reset-password",
            headers=csrf(client),
            json={"token": reset, "password": "another-entirely-new-pass"},
        ).status_code
        == 400
    )


def test_wrong_recovery_factors_have_generic_response_and_send_no_email(recovery_env):
    client, factory, sent, _ = recovery_env
    register_and_verify(client, sent)
    with factory() as db:
        user = db.scalar(select(User))
        user.date_of_birth = date(2000, 1, 2)
        db.commit()
    initial = len(sent)
    data = {
        "email": "a@example.com",
        "date_of_birth": "2001-01-02",
        "remembered_password": "very-long-passphrase-1",
    }
    wrong = client.post("/api/v1/auth/recover", headers=csrf(client), json=data)
    data["email"] = "unknown@example.com"
    unknown = client.post("/api/v1/auth/recover", headers=csrf(client), json=data)
    assert wrong.status_code == unknown.status_code == 202
    assert wrong.json() == unknown.json() and len(sent) == initial
    with factory() as db:
        assert db.scalar(select(ActionToken).where(ActionToken.purpose == "reset")) is None
