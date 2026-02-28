"""Google OAuth token validation unit tests"""

import os
from unittest import TestCase
from unittest.mock import patch

from google.auth.exceptions import GoogleAuthError

from utils.auth.google import verify_google_token

FAKE_CLIENT_ID = "test-client-id.apps.googleusercontent.com"
FAKE_TOKEN = "eyJhbGciOiJSUzI1NiJ9.fake.token"
FAKE_SUB = "116954529561234567890"


class TestVerifyGoogleToken(TestCase):
    """Unit tests for Google OAuth token validation"""

    @patch.dict(os.environ, {"GOOGLE_CLIENT_ID": FAKE_CLIENT_ID})
    @patch("utils.auth.google.id_token.verify_oauth2_token")
    def test_valid_token(self, mock_verify):
        """A valid token returns the sub claim"""
        mock_verify.return_value = {
            "sub": FAKE_SUB,
            "email": "user@example.com",
            "email_verified": True,
        }

        result = verify_google_token(FAKE_TOKEN)

        self.assertEqual(FAKE_SUB, result)
        mock_verify.assert_called_once()

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_client_id(self):
        """Raises ValueError when GOOGLE_CLIENT_ID is not configured"""
        # Ensure GOOGLE_CLIENT_ID is not set
        os.environ.pop("GOOGLE_CLIENT_ID", None)

        self.assertRaises(ValueError, verify_google_token, FAKE_TOKEN)

    @patch.dict(os.environ, {"GOOGLE_CLIENT_ID": FAKE_CLIENT_ID})
    @patch("utils.auth.google.id_token.verify_oauth2_token")
    def test_invalid_token(self, mock_verify):
        """Raises ValueError when token validation fails"""
        mock_verify.side_effect = ValueError("Token expired")

        self.assertRaises(ValueError, verify_google_token, FAKE_TOKEN)

    @patch.dict(os.environ, {"GOOGLE_CLIENT_ID": FAKE_CLIENT_ID})
    @patch("utils.auth.google.id_token.verify_oauth2_token")
    def test_wrong_issuer(self, mock_verify):
        """Raises ValueError when token has wrong issuer"""
        mock_verify.side_effect = GoogleAuthError("Wrong issuer")

        self.assertRaises(ValueError, verify_google_token, FAKE_TOKEN)

    @patch.dict(os.environ, {"GOOGLE_CLIENT_ID": FAKE_CLIENT_ID})
    @patch("utils.auth.google.id_token.verify_oauth2_token")
    def test_missing_sub_claim(self, mock_verify):
        """Raises ValueError when token is missing sub claim"""
        mock_verify.return_value = {
            "email": "user@example.com",
            "email_verified": True,
        }

        self.assertRaises(ValueError, verify_google_token, FAKE_TOKEN)
