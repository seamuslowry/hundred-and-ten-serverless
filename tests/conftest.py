"""Helpers to perform common functions during testing"""

import pytest
from fastapi.testclient import TestClient

from function_app import fastapi_app


@pytest.fixture
def client():
    """A fixture client for Fast API. Using context for lifecycle."""
    with TestClient(fastapi_app) as test_client:
        yield test_client
