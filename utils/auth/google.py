"""Google OAuth ID token validation"""

import cachecontrol
import google.auth.transport.requests
import requests
from google.auth.exceptions import GoogleAuthError
from google.oauth2 import id_token

from utils.auth.identity import Identity

# Module-level cached session for Google's public key fetches.
# CacheControl respects Cache-Control headers from Google's cert endpoint,
# avoiding a network round-trip on every token validation (keys rotate ~daily).
_session = requests.session()
_cached_session = cachecontrol.CacheControl(_session)
_request = google.auth.transport.requests.Request(session=_cached_session)

AUDIENCE = "80097063421-no8el98n0f188in9pur04r9h8sh7rsen.apps.googleusercontent.com"


def verify_google_token(token: str) -> Identity:
    """
    Validate a Google OAuth ID token and return the user's identity.

    Validates the token's signature, audience, expiry, and issuer against
    Google's public keys. Returns an Identity populated from token claims.

    Args:
        token: The encoded Google ID token from the client.

    Returns:
        An Identity with the user's id, name, and picture URL.

    Raises:
        ValueError: If the token is invalid/expired, or the token is missing the ``sub`` claim.
    """

    try:
        id_info = id_token.verify_oauth2_token(token, _request, AUDIENCE)
    except (ValueError, GoogleAuthError) as exc:
        raise ValueError(f"Invalid Google token: {exc}") from exc

    sub = id_info.get("sub")
    if not sub:
        raise ValueError("Token missing sub claim")

    return Identity(
        id=sub,
        name=id_info.get("name"),
        picture_url=id_info.get("picture"),
    )
