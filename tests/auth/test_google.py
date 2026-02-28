"""Google OAuth token validation unit tests"""

from unittest import TestCase
from unittest.mock import patch

from google.auth.exceptions import GoogleAuthError

from utils.auth.google import verify_google_token

FAKE_TOKEN = "eyJhbGciOiJSUzI1NiJ9.fake.token"
FAKE_SUB = "116954529561234567890"


class TestVerifyGoogleToken(TestCase):
    """Unit tests for Google OAuth token validation"""

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

    @patch("utils.auth.google.id_token.verify_oauth2_token")
    def test_invalid_token(self, mock_verify):
        """Raises ValueError when token validation fails"""
        mock_verify.side_effect = ValueError("Token expired")

        self.assertRaises(ValueError, verify_google_token, FAKE_TOKEN)

    @patch("utils.auth.google.id_token.verify_oauth2_token")
    def test_wrong_issuer(self, mock_verify):
        """Raises ValueError when token has wrong issuer"""
        mock_verify.side_effect = GoogleAuthError("Wrong issuer")

        self.assertRaises(ValueError, verify_google_token, FAKE_TOKEN)

    @patch("utils.auth.google.id_token.verify_oauth2_token")
    def test_missing_sub_claim(self, mock_verify):
        """Raises ValueError when token is missing sub claim"""
        mock_verify.return_value = {
            "email": "user@example.com",
            "email_verified": True,
        }

        self.assertRaises(ValueError, verify_google_token, FAKE_TOKEN)
