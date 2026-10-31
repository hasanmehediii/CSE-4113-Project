"""Google-specific verification boundary; replace in tests, reuse session lifecycle."""

from fastapi import HTTPException
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2 import id_token

from app.core.config import get_settings


class GoogleProvider:
    def verify(self, credential: str) -> dict:
        client_id = get_settings().google_client_id
        if not client_id:
            raise HTTPException(503, "Google sign-in is not configured")
        try:
            return id_token.verify_oauth2_token(credential, Request(), client_id)
        except ValueError:
            raise HTTPException(401, "Invalid Google credential")
        except GoogleAuthError:
            raise HTTPException(503, "Google sign-in temporarily unavailable")


def get_google_provider():
    return GoogleProvider()
