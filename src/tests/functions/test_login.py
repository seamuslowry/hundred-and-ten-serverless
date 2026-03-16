"""Unit tests to create / update user as a client"""

from time import time

from fastapi.testclient import TestClient

from src.main.models.internal import User
from src.tests.helpers import user


def test_create_user(client: TestClient):
    """Can create a new user"""
    player_id = f"{time()}"
    u = user(client, User(player_id=player_id, name='Name'))

    assert player_id == u["id"]


def test_refresh_user(client: TestClient):
    """Can refresh an existing user"""
    player_id = f"{time()}"
    initial_name = 'Initial'
    updated_name = 'Updated'
    u = user(client, User(player_id=player_id, name=initial_name))

    assert player_id == u["id"]
    assert initial_name == u["name"]

    u = user(client, User(player_id=player_id, name=updated_name))
    assert player_id == u["id"]
    assert updated_name == u["name"]
