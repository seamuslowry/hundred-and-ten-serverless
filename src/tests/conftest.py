"""Helpers to perform common functions during testing"""

import pytest
from fastapi.testclient import TestClient

from function_app import fastapi_app

DEFAULT_ID = "id"


@pytest.fixture
def client():
    with TestClient(fastapi_app) as test_client:
        yield test_client
