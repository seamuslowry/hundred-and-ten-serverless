"""Init the auth module"""

from .depends import get_authorized_identity, get_identity
from .firebase import verify_firebase_token
from .identity import Identity

__all__ = [
    "Identity",
    "verify_firebase_token",
    "get_identity",
    "get_authorized_identity",
]
