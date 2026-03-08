"""Init the auth module"""

from .depends import get_authorized_identity, get_identity
from .google import verify_google_token
from .identity import Identity

__all__ = ["Identity", "verify_google_token", "get_identity", "get_authorized_identity"]
