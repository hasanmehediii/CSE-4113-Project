import hashlib
import hmac
import secrets
import time
from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

hasher = PasswordHasher()


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def random_token() -> str:
    return secrets.token_urlsafe(32)


@lru_cache
def dummy_hash() -> str:
    return hasher.hash(random_token())


def verify_password(stored: str | None, password: str) -> bool:
    try:
        valid = hasher.verify(stored or dummy_hash(), password)
        return bool(stored) and valid
    except (VerificationError, InvalidHashError):
        return False


def csrf_signature(secret: str, payload: str, session_token: str) -> str:
    return hmac.new(
        secret.encode(), f"{payload}:{session_token}".encode(), hashlib.sha256
    ).hexdigest()


def make_csrf(secret: str, session_token: str = "") -> str:
    payload = f"{int(time.time())}.{random_token()}"
    return f"{payload}.{csrf_signature(secret, payload, session_token)}"


def valid_csrf(token: str, secret: str, lifetime: int, session_token: str) -> bool:
    try:
        issued, nonce, signature = token.split(".")
        age = time.time() - int(issued)
        return 0 <= age <= lifetime and hmac.compare_digest(
            signature, csrf_signature(secret, f"{issued}.{nonce}", session_token)
        )
    except (ValueError, TypeError):
        return False
