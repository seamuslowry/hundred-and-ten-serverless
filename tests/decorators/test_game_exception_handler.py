"""Decorator unit tests"""

from unittest import TestCase
from unittest.mock import patch

import azure.functions as func

from tests.helpers import build_request
from utils.auth import Identity
from utils.decorators.authentication import get_identity, handle_authentication
from utils.decorators.error_aggregation import handle_error
from utils.errors import AuthenticationError, AuthorizationError
from utils.models import HundredAndTenError


class TestErrorHandler(TestCase):
    """Error handler unit tests"""

    def test_does_nothing_when_no_exception(self):
        """Function returns as expected when no exception occurs"""
        status_code = 204
        wrapped_func = handle_error(
            lambda r: func.HttpResponse(status_code=status_code)
        )

        self.assertEqual(status_code, wrapped_func(build_request()).status_code)

    def test_returns_400_for_game_error(self):
        """Function returns 400 when a game error occurs"""

        def test_func(req):
            raise HundredAndTenError("")

        wrapped_func = handle_error(test_func)

        self.assertEqual(400, wrapped_func(build_request()).status_code)

    def test_returns_401_for_authentication_error(self):
        """Function returns 401 when an AuthenticationError occurs"""

        def test_func(req):
            raise AuthenticationError("bad token")

        wrapped_func = handle_error(test_func)

        self.assertEqual(401, wrapped_func(build_request()).status_code)

    def test_returns_403_for_authorization_error(self):
        """Function returns 403 when an AuthorizationError occurs"""

        def test_func(req):
            raise AuthorizationError("forbidden")

        wrapped_func = handle_error(test_func)

        self.assertEqual(403, wrapped_func(build_request()).status_code)


class TestAuthentication(TestCase):
    """Authentication decorator unit tests"""

    @patch(
        "utils.decorators.authentication.verify_google_token",
        return_value=Identity(
            id="user-123", name="Test User", picture_url="https://example.com/pic.jpg"
        ),
    )
    def test_sets_identity_on_request(self, mock_verify):
        """Valid Bearer token sets identity in context"""

        def capture_identity(_):
            identity = get_identity()
            self.assertEqual("user-123", identity.id)
            self.assertEqual("Test User", identity.name)
            self.assertEqual("https://example.com/pic.jpg", identity.picture_url)
            return func.HttpResponse(status_code=200)

        wrapped = handle_authentication(capture_identity)
        req = build_request(headers={"authorization": "Bearer valid.token"})
        wrapped(req)

        mock_verify.assert_called_once_with("valid.token")

    def test_raises_authentication_error_without_bearer(self):
        """Missing Bearer token raises AuthenticationError"""
        wrapped = handle_authentication(lambda r: func.HttpResponse(status_code=200))
        req = build_request(headers={"authorization": ""})

        self.assertRaises(AuthenticationError, wrapped, req)

    def test_raises_authentication_error_without_auth_header(self):
        """Missing Authorization header entirely raises AuthenticationError"""
        wrapped = handle_authentication(lambda r: func.HttpResponse(status_code=200))
        req = func.HttpRequest(method="GET", body=b"", url="", headers={})

        self.assertRaises(AuthenticationError, wrapped, req)

    @patch(
        "utils.decorators.authentication.verify_google_token",
        side_effect=ValueError("Invalid token"),
    )
    def test_raises_authentication_error_for_invalid_token(self, _):
        """Invalid token raises AuthenticationError"""
        wrapped = handle_authentication(lambda r: func.HttpResponse(status_code=200))
        req = build_request(headers={"authorization": "Bearer bad.token"})

        self.assertRaises(AuthenticationError, wrapped, req)
