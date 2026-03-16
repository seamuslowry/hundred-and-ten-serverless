"""Firebase ID token validation"""

import cachecontrol
import google.auth.transport.requests
import requests
from google.oauth2 import id_token

from .identity import Identity

FIREBASE_PROJECT_ID = "hundred-and-ten"
CERTS = "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"
ISSUER = f"https://securetoken.google.com/{FIREBASE_PROJECT_ID}"

# Module-level cached session for Google's public key fetches.
# CacheControl respects Cache-Control headers from Google's cert endpoint,
# avoiding a network round-trip on every token validation.
_session = requests.Session()
_cached_session = cachecontrol.CacheControl(_session)
_request = google.auth.transport.requests.Request(session=_cached_session)


def verify_firebase_token(token: str) -> Identity:
    """
    Validate a Firebase ID token and return the user's identity.

    Validates the token's signature, audience, expiry, and issuer against
    Firebase's public keys. Returns an Identity populated from token claims.

    Args:
        token: The encoded Firebase ID token from the client.

    Returns:
        An Identity with the user's id, name, and picture URL.

    Raises:
        ValueError: If the token is invalid/expired, or the token is missing the ``sub`` claim.
    """

    try:
        # Verify signature + standard claims
        id_info = id_token.verify_token(
            token,
            _request,
            audience=FIREBASE_PROJECT_ID,
            certs_url=CERTS,
        )
    except Exception as exc:
        raise ValueError(f"Invalid Firebase token: {exc}") from exc

    sub = id_info.get("sub")
    if not sub:
        raise ValueError("Token missing sub claim")

    iss = id_info.get("iss")
    if iss != ISSUER:
        raise ValueError(f"Invalid issuer {iss}")

    return Identity(
        id=sub,
        name=id_info.get("name"),
        picture_url=id_info.get("picture"),
    )
