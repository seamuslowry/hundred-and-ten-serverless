"""Shared test fixtures"""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _mock_google_auth():
    """Bypass Google token validation in all tests.

    The mock makes verify_google_token return the token as-is,
    so ``Authorization: Bearer some-user`` resolves to identifier ``some-user``.
    """
    with patch(
        "utils.decorators.authentication.verify_google_token",
        side_effect=lambda token: token,
    ):
        yield
