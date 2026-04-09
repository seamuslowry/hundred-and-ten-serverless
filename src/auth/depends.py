"""Identity retrieval as dependency to HTTP endpoints"""

from fastapi import Depends, Path
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.models.internal.errors import AuthenticationError, AuthorizationError

from .firebase import verify_firebase_token
from .identity import Identity

# =============================================================================
# Authentication dependency
# =============================================================================

http_bearer = HTTPBearer(
    description="A Firebase ID token",
)


def get_authenticated_identity(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
) -> Identity:
    """Validate the Bearer token and return the authenticated identity"""
    try:
        return verify_firebase_token(credentials.credentials)
    except ValueError as exc:
        raise AuthenticationError(str(exc)) from exc


def get_authorized_identity_for_path_player(
    player_id: str = Path(), identity: Identity = Depends(get_authenticated_identity)
):
    """Retrieve the authenticated identity and authorize it for the path"""
    if identity.id != player_id:
        raise AuthorizationError(f"{identity.id} cannot act as {player_id}")

    return identity
