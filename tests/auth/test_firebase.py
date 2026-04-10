"""Google OAuth token validation unit tests"""

from unittest.mock import patch

import pytest

from src.auth.firebase import ISSUER, verify_firebase_token

FAKE_TOKEN = "eyJhbGciOiJSUzI1NiJ9.fake.token"
FAKE_SUB = "116954529561234567890"


@patch("src.auth.firebase.id_token.verify_token")
def test_valid_token(mock_verify):
    """A valid token returns an Identity with id, name, and picture_url"""
    mock_verify.return_value = {
        "sub": FAKE_SUB,
        "name": "Test User",
        "picture": "https://example.com/photo.jpg",
        "email": "user@example.com",
        "email_verified": True,
        "iss": ISSUER,
    }

    result = verify_firebase_token(FAKE_TOKEN)

    assert FAKE_SUB == result.id
    assert "Test User" == result.name
    assert "https://example.com/photo.jpg" == result.picture_url
    mock_verify.assert_called_once()


@patch("src.auth.firebase.id_token.verify_token")
def test_invalid_token(mock_verify):
    """Raises ValueError when token validation fails"""
    mock_verify.side_effect = ValueError("Token expired")

    with pytest.raises(ValueError):
        verify_firebase_token(FAKE_TOKEN)


@patch("src.auth.firebase.id_token.verify_token")
def test_wrong_issuer(mock_verify):
    """Raises ValueError when token has wrong issuer"""
    mock_verify.return_value = {
        "sub": FAKE_SUB,
        "name": "Test User",
        "picture": "https://example.com/photo.jpg",
        "email": "user@example.com",
        "email_verified": True,
        "iss": "wrong-issuer",
    }

    with pytest.raises(ValueError):
        verify_firebase_token(FAKE_TOKEN)


@patch("src.auth.firebase.id_token.verify_token")
def test_missing_sub_claim(mock_verify):
    """Raises ValueError when token is missing sub claim"""
    mock_verify.return_value = {
        "email": "user@example.com",
        "email_verified": True,
    }

    with pytest.raises(ValueError):
        verify_firebase_token(FAKE_TOKEN)
