"""Exception handler and authentication unit tests"""

from unittest.mock import patch

from beanie import PydanticObjectId
from fastapi.testclient import TestClient

from src.auth import Identity
from src.models.internal.errors import AuthorizationError
from tests.helpers import DEFAULT_ID


@patch(
    "src.auth.depends.verify_firebase_token",
    side_effect=lambda token: Identity(id=token),
)
@patch(
    "src.routers.games.GameService.get",
    side_effect=AuthorizationError("forbidden"),
)
def test_returns_403_for_authorization_error(_mock_get, _mock_auth, client: TestClient):
    """Endpoint returns 403 when an AuthorizationError occurs"""
    resp = client.get(
        f"/players/{DEFAULT_ID}/games/{PydanticObjectId()}",
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    )
    assert 403 == resp.status_code


def test_returns_401_for_no_bearer(client: TestClient):
    """Endpoint returns 401 when no Bearer token is provided"""
    resp = client.get(
        f"/players/{DEFAULT_ID}/games/some-id",
        headers={"authorization": ""},
    )
    assert 401 == resp.status_code


def test_returns_401_without_auth_header(client: TestClient):
    """Endpoint returns 401 when Authorization header is missing entirely"""
    resp = client.get(f"/players/{DEFAULT_ID}/games/some-id")
    assert 401 == resp.status_code


@patch(
    "src.auth.depends.verify_firebase_token",
    side_effect=ValueError("Invalid token"),
)
def test_returns_401_for_invalid_token(_, client: TestClient):
    """Endpoint returns 401 when token validation fails"""
    resp = client.get(
        f"/players/{DEFAULT_ID}/games/some-id",
        headers={"authorization": "Bearer bad.token"},
    )
    assert 401 == resp.status_code


@patch(
    "src.auth.depends.verify_firebase_token",
    return_value=Identity(
        id="user-123", name="Test User", picture_url="https://example.com/pic.jpg"
    ),
)
def test_valid_token_authenticates(mock_verify, client: TestClient):
    """Valid Bearer token authenticates the user"""
    # This will still fail with 400 because "some-id" is invalid,
    # but authentication succeeds (not 401)
    resp = client.get(
        "/players/valid.token/games/some-id",
        headers={"authorization": "Bearer valid.token"},
    )
    # The fact that we get 400 (not 401) proves authentication passed
    assert 401 != resp.status_code
    mock_verify.assert_called_once_with("valid.token")


@patch(
    "src.auth.depends.verify_firebase_token",
    return_value=Identity(id="user-123", name="Test User"),
)
def test_raises_authorization_error_when_wrong_idenity(_, client: TestClient):
    """Missing Bearer token returns 403"""
    resp = client.get(
        "/players/some-id/games/some-id",
        headers={"authorization": "Bearer unknown"},
    )
    assert 403 == resp.status_code
