"""Identity retrieval as dependency to HTTP endpoints"""

from fastapi import Depends, Path
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from utils.errors import AuthenticationError, AuthorizationError

from .google import verify_google_token
from .identity import Identity

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


def get_authorized_identity(
    player_id: str = Path(), identity: Identity = Depends(get_identity)
):
    """Retrieve the authenticated identity and authorize it for the path"""
    if identity.id != player_id:
        raise AuthorizationError(f"{identity.id} cannot act as {player_id}")

    return identity
