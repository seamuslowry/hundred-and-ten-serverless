"""Shared test fixtures"""

from unittest.mock import patch

import pytest

from src.main.auth import Identity


@pytest.fixture(autouse=True)
def _mock_firebase_auth():
    """Bypass Firebase token validation in all tests.

    The mock makes verify_firebase_token return an Identity with the token as the id,
    so ``Authorization: Bearer some-user`` resolves to Identity(id="some-user").
    """
    with patch(
        "src.main.auth.depends.verify_firebase_token",
        side_effect=lambda token: Identity(id=token),
    ):
        yield
