"""Google OAuth token validation unit tests"""

from unittest.mock import patch

import pytest
from google.auth.exceptions import GoogleAuthError

from src.main.auth.google import verify_google_token

FAKE_TOKEN = "eyJhbGciOiJSUzI1NiJ9.fake.token"
FAKE_SUB = "116954529561234567890"


class TestVerifyGoogleToken:
    """Unit tests for Google OAuth token validation"""

    @patch("src.main.auth.google.id_token.verify_oauth2_token")
    def test_valid_token(self, mock_verify):
        """A valid token returns an Identity with id, name, and picture_url"""
        mock_verify.return_value = {
            "sub": FAKE_SUB,
            "name": "Test User",
            "picture": "https://example.com/photo.jpg",
            "email": "user@example.com",
            "email_verified": True,
        }

        result = verify_google_token(FAKE_TOKEN)

        assert FAKE_SUB == result.id
        assert "Test User" == result.name
        assert "https://example.com/photo.jpg" == result.picture_url
        mock_verify.assert_called_once()

    @patch("src.main.auth.google.id_token.verify_oauth2_token")
    def test_invalid_token(self, mock_verify):
        """Raises ValueError when token validation fails"""
        mock_verify.side_effect = ValueError("Token expired")

        with pytest.raises(ValueError):
            verify_google_token(FAKE_TOKEN)

    @patch("src.main.auth.google.id_token.verify_oauth2_token")
    def test_wrong_issuer(self, mock_verify):
        """Raises ValueError when token has wrong issuer"""
        mock_verify.side_effect = GoogleAuthError("Wrong issuer")

        with pytest.raises(ValueError):
            verify_google_token(FAKE_TOKEN)

    @patch("src.main.auth.google.id_token.verify_oauth2_token")
    def test_missing_sub_claim(self, mock_verify):
        """Raises ValueError when token is missing sub claim"""
        mock_verify.return_value = {
            "email": "user@example.com",
            "email_verified": True,
        }

        with pytest.raises(ValueError):
            verify_google_token(FAKE_TOKEN)
