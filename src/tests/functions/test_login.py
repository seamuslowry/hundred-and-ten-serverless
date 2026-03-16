"""Unit tests to create / update players as a client"""

from time import time

from fastapi.testclient import TestClient

from src.main.models.internal import Player
from src.tests.helpers import player


def test_create_player(client: TestClient):
    """Can create a new player"""
    player_id = f"{time()}"
    u = player(client, Player(player_id=player_id, name="Name"))

    assert player_id == u["id"]


def test_refresh_player(client: TestClient):
    """Can refresh an existing player"""
    player_id = f"{time()}"
    initial_name = "Initial"
    updated_name = "Updated"
    u = player(client, Player(player_id=player_id, name=initial_name))

    assert player_id == u["id"]
    assert initial_name == u["name"]

    u = player(client, Player(player_id=player_id, name=updated_name))
    assert player_id == u["id"]
    assert updated_name == u["name"]
