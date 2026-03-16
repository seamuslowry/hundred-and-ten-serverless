"""Helpers to perform common functions during testing"""

from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main.auth import Identity
from src.main.models.internal import Player

DEFAULT_ID = "id"


def lobby_game(
    test_client: TestClient, organizer: str = DEFAULT_ID, name: str = "test game"
) -> dict[str, Any]:
    """Get a lobby waiting for the players"""
    resp = test_client.post(
        f"/players/{organizer}/lobbies/create",
        json={"name": name},
        headers={"authorization": f"Bearer {organizer}"},
    )
    return resp.json()


def user(test_client: TestClient, new_user: Player) -> dict[str, Any]:
    """Update an existing user if possible"""
    with patch(
        "src.main.auth.depends.verify_firebase_token",
        side_effect=lambda _: Identity(
            id=new_user.player_id,
            name=new_user.name or "",
            picture_url=new_user.picture_url,
        ),
    ):
        resp = test_client.put(
            f"/players/{new_user.player_id}/self",
            headers={"authorization": f"Bearer {new_user.player_id}"},
        )
    return resp.json()


def started_game(
    test_client: TestClient, organizer=DEFAULT_ID, name="test game"
) -> dict[str, Any]:
    """Get a started game waiting for the first move"""
    created_lobby = lobby_game(test_client, organizer=organizer, name=name)
    organizer = created_lobby["organizer"]["id"]
    resp = test_client.post(
        f"/players/{organizer}/lobbies/{created_lobby['id']}/start",
        headers={"authorization": f"Bearer {organizer}"},
    )
    return resp.json()


def completed_game(test_client: TestClient) -> dict[str, Any]:
    """Get a completed game"""
    game = started_game(test_client)

    active_player = game["round"]["active_player"]
    assert active_player

    resp = test_client.post(
        f"/players/{active_player['id']}/games/{game['id']}/leave",
        headers={"authorization": f"Bearer {active_player['id']}"},
    )
    return resp.json()


def request_suggestion(
    test_client: TestClient, game_id: str, player_id: str = DEFAULT_ID
):
    """get the suggestion for the game"""
    return test_client.get(
        f"/players/{player_id}/games/{game_id}/suggestion",
        headers={"authorization": f"Bearer {player_id}"},
    )


def get_suggestion(test_client: TestClient, game_id: str) -> dict[str, Any]:
    """get the suggestion for the game"""
    resp = request_suggestion(test_client, game_id)
    return resp.json()
