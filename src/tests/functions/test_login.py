"""Unit tests to create / update user as a client"""

from time import time

from fastapi.testclient import TestClient

from src.main.models.internal import User
from src.tests.helpers import user


def test_create_user(client: TestClient):
    """Can create a new user"""
    identifier = f"{time()}"
    u = user(client, User(player_id=identifier, name='Name'))

    assert identifier == u["identifier"]


def test_refresh_user(client: TestClient):
    """Can refresh an existing user"""
    identifier = f"{time()}"
    initial_name = 'Initial'
    updated_name = 'Updated'
    u = user(client, User(player_id=identifier, name=initial_name))

    assert identifier == u["identifier"]
    assert initial_name == u["name"]

    u = user(client, User(player_id=identifier, name=updated_name))
    assert identifier == u["identifier"]
    assert updated_name == u["name"]
