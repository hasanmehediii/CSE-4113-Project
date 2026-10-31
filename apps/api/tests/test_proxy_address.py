import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core import rate_limit
from app.core.config import get_settings


@pytest.mark.parametrize("peer,forwarded,expected", [
    ("172.24.0.1", None, "172.24.0.1"),  # Direct Docker port: no proxy header.
    ("172.24.0.2", "203.0.113.10", "203.0.113.10"),
    ("172.24.0.2", "2001:db8::1", "2001:db8::1"),
    ("203.0.113.20", "203.0.113.10", "203.0.113.20"),  # Untrusted spoof ignored.
])
def test_direct_and_proxied_auth_requests_choose_the_correct_rate_bucket(monkeypatch, peer, forwarded, expected):
    monkeypatch.setattr(get_settings(), "trusted_proxy_cidrs", ["172.24.0.0/16"])
    captured = []
    monkeypatch.setattr(rate_limit, "enforce", lambda request, scope, identity, capacity, period: captured.append(identity))
    headers = [] if forwarded is None else [(b"x-real-ip", forwarded.encode())]
    request = Request({"type": "http", "client": (peer, 1234), "headers": headers})
    rate_limit.auth_ip_limit(request)
    assert captured == [expected]


@pytest.mark.parametrize("forwarded", ["", "bad-address", "203.0.113.1, 203.0.113.2"])
def test_malformed_address_from_trusted_proxy_remains_rejected(monkeypatch, forwarded):
    monkeypatch.setattr(get_settings(), "trusted_proxy_cidrs", ["172.24.0.0/16"])
    request = Request({"type": "http", "client": ("172.24.0.2", 1234),
                       "headers": [(b"x-real-ip", forwarded.encode())]})
    with pytest.raises(HTTPException) as error:
        rate_limit.auth_ip_limit(request)
    assert error.value.status_code == 400
