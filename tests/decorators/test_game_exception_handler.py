"""Exception handler and authentication unit tests"""

from unittest import TestCase
from unittest.mock import patch

from tests.helpers import DEFAULT_ID, get_client
from utils.auth import Identity
from utils.errors import AuthorizationError


class TestErrorHandler(TestCase):
    """Error handler unit tests"""

    @patch(
        "function_app.verify_google_token",
        side_effect=lambda token: Identity(id=token),
    )
    def test_returns_400_for_game_error(self, _):
        """Endpoint returns 400 when a game error occurs"""
        client = get_client()
        # Use an invalid game_id to trigger a game error from GameService.get
        resp = client.get(
            "/info/not-a-valid-id",
            headers={"authorization": f"Bearer {DEFAULT_ID}"},
        )
        self.assertEqual(400, resp.status_code)

    @patch(
        "function_app.verify_google_token",
        side_effect=lambda token: Identity(id=token),
    )
    @patch(
        "function_app.GameService.get",
        side_effect=AuthorizationError("forbidden"),
    )
    def test_returns_403_for_authorization_error(self, _mock_get, _mock_auth):
        """Endpoint returns 403 when an AuthorizationError occurs"""
        client = get_client()
        resp = client.get(
            "/info/some-id",
            headers={"authorization": f"Bearer {DEFAULT_ID}"},
        )
        self.assertEqual(403, resp.status_code)

    def test_returns_403_for_authentication_error(self):
        """Endpoint returns 403 when no Bearer token is provided"""
        client = get_client()
        resp = client.get(
            "/info/some-id",
            headers={"authorization": ""},
        )
        self.assertEqual(403, resp.status_code)

    def test_returns_403_without_auth_header(self):
        """Endpoint returns 403 when Authorization header is missing entirely"""
        client = get_client()
        resp = client.get("/info/some-id")
        self.assertEqual(403, resp.status_code)

    @patch(
        "function_app.verify_google_token",
        side_effect=ValueError("Invalid token"),
    )
    def test_returns_401_for_invalid_token(self, _):
        """Endpoint returns 401 when token validation fails"""
        client = get_client()
        resp = client.get(
            "/info/some-id",
            headers={"authorization": "Bearer bad.token"},
        )
        self.assertEqual(401, resp.status_code)


class TestAuthentication(TestCase):
    """Authentication unit tests"""

    @patch(
        "function_app.verify_google_token",
        return_value=Identity(
            id="user-123", name="Test User", picture_url="https://example.com/pic.jpg"
        ),
    )
    def test_valid_token_authenticates(self, mock_verify):
        """Valid Bearer token authenticates the user"""
        client = get_client()
        # This will still fail with 400 because "some-id" is invalid,
        # but authentication succeeds (not 401)
        resp = client.get(
            "/info/some-id",
            headers={"authorization": "Bearer valid.token"},
        )
        # The fact that we get 400 (not 401) proves authentication passed
        self.assertNotEqual(401, resp.status_code)
        mock_verify.assert_called_once_with("valid.token")

    def test_raises_authentication_error_without_bearer(self):
        """Missing Bearer token returns 403"""
        client = get_client()
        resp = client.get(
            "/info/some-id",
            headers={"authorization": ""},
        )
        self.assertEqual(403, resp.status_code)

    def test_raises_authentication_error_without_auth_header(self):
        """Missing Authorization header entirely returns 403"""
        client = get_client()
        resp = client.get("/info/some-id", headers={})
        self.assertEqual(403, resp.status_code)

    @patch(
        "function_app.verify_google_token",
        side_effect=ValueError("Invalid token"),
    )
    def test_raises_authentication_error_for_invalid_token(self, _):
        """Invalid token returns 401"""
        client = get_client()
        resp = client.get(
            "/info/some-id",
            headers={"authorization": "Bearer bad.token"},
        )
        self.assertEqual(401, resp.status_code)
