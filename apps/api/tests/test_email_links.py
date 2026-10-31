from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlsplit

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.services.email_service import send_action_email


@pytest.mark.parametrize("purpose,route", [("verify", "verify-email"), ("reset", "reset-password")])
def test_email_links_use_configured_origin_and_fragment(monkeypatch, purpose, route):
    settings = Settings(_env_file=None, frontend_url="https://dubsi.example/")
    monkeypatch.setattr("app.services.email_service.get_settings", lambda: settings)
    smtp = MagicMock()
    monkeypatch.setattr("app.services.email_service.smtplib.SMTP", smtp)
    token = "one-time-token-with/special+characters"
    send_action_email("resident@example.com", token, purpose)
    message = smtp.return_value.__enter__.return_value.send_message.call_args.args[0]
    link = next(line for line in message.get_content().splitlines() if line.startswith("https://"))
    url = urlsplit(link)
    assert url.netloc == "dubsi.example"
    assert url.path == f"/{route}"
    assert not url.query
    assert parse_qs(url.fragment)["token"] == [token]
    assert message["To"] == "resident@example.com"


@pytest.mark.parametrize("origin", ["javascript:alert(1)", "https://user:pass@example.com", "https://example.com/path", "https://example.com?next=evil", "https://example.com#fragment"])
def test_frontend_origin_rejects_unsafe_values(origin):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, frontend_url=origin)
