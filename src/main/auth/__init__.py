"""Init the auth module"""

from .depends import get_authenticated_identity, get_authorized_identity_for_path_player
from .firebase import verify_firebase_token
from .identity import Identity

__all__ = [
    "Identity",
    "verify_firebase_token",
    "get_authenticated_identity",
    "get_authorized_identity_for_path_player",
]
