import pytest
import test_auth
from sqlalchemy import func, select

from app.core.config import Settings
from app.core.security import verify_password
from app.models.user import User
from app.workers.bootstrap import bootstrap


@pytest.fixture
def bootstrap_env(monkeypatch):
    yield from test_auth.auth_env.__wrapped__(monkeypatch)


def test_bootstrapped_admin_can_login_with_eight_character_password(bootstrap_env):
    client, factory, _, _ = bootstrap_env
    settings = Settings(
        _env_file=None,
        admin_email="mayor@example.com",
        admin_password="pass1234",
        admin_name="Test Mayor",
    )
    with factory() as db:
        bootstrap(db, settings)
        db.commit()
    result = client.post(
        "/api/v1/auth/login",
        headers=test_auth.csrf(client),
        json={"identifier": settings.admin_email, "password": settings.admin_password},
    )
    assert result.status_code == 200, result.text
    assert result.json()["role"] == "admin"
    assert result.json()["email_verified"] is True
    assert client.get("/api/v1/auth/me").json()["name"] == "Test Mayor"


@pytest.mark.parametrize("password", ["x" * 7, "x" * 129])
def test_bootstrap_rejects_passwords_outside_shared_limits(bootstrap_env, password):
    _, factory, _, _ = bootstrap_env
    settings = Settings(_env_file=None, admin_email="mayor@example.com", admin_password=password)
    with factory() as db:
        with pytest.raises(ValueError, match="ADMIN_PASSWORD must be 8–128 characters"):
            bootstrap(db, settings)
        assert db.scalar(select(func.count()).select_from(User)) == 0


def test_bootstrap_keeps_existing_admin_password(bootstrap_env):
    _, factory, _, _ = bootstrap_env
    settings = Settings(
        _env_file=None, admin_email="mayor@example.com", admin_password="original-password"
    )
    with factory() as db:
        bootstrap(db, settings)
        db.commit()
        settings.admin_password = "different-password"
        assert "password unchanged" in bootstrap(db, settings)
        db.commit()
        user = db.scalar(select(User).where(User.email == settings.admin_email))
        assert verify_password(user.password_hash, "original-password")
        assert not verify_password(user.password_hash, settings.admin_password)
        assert db.scalar(select(func.count()).select_from(User)) == 1
