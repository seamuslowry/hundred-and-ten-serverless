"""Identity retrieval as dependency to HTTP endpoints"""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from utils.auth.google import verify_google_token
from utils.auth.identity import Identity
from utils.errors import AuthenticationError

# =============================================================================
# Authentication dependency
# =============================================================================

google_bearer = HTTPBearer(
    description="A Google OAuth2 ID token",
)


def get_identity(
    credentials: HTTPAuthorizationCredentials = Depends(google_bearer),
) -> Identity:
    """Validate the Bearer token and return the authenticated identity"""
    try:
        return verify_google_token(credentials.credentials)
    except ValueError as exc:
        raise AuthenticationError(str(exc)) from exc
