"""Helpers to perform common functions during testing"""

from typing import Any

from fastapi.testclient import TestClient

from src.main.models.internal import User

DEFAULT_ID = "id"


def lobby_game(
    test_client: TestClient,
    organizer: str = DEFAULT_ID,
) -> dict[str, Any]:
    """Get a lobby waiting for the players"""
    resp = test_client.post(
        f"/players/{organizer}/lobbies/create",
        json={"name": "test game"},
        headers={"authorization": f"Bearer {organizer}"},
    )
    return resp.json()


def create_user(
    test_client: TestClient, identifier: str, name: str = ""
) -> dict[str, Any]:
    """Attempt to create a user for the first time"""
    return __user(test_client, "POST", User(identifier=identifier, name=name))


def update_user(
    test_client: TestClient, identifier: str, name: str = ""
) -> dict[str, Any]:
    """Update an existing user if possible"""
    return __user(test_client, "PUT", User(identifier=identifier, name=name))


def __user(test_client: TestClient, method: str, user: User) -> dict[str, Any]:
    """Update an existing user if possible"""
    resp = test_client.request(
        method,
        f"/players/{user.identifier}",
        json={"name": user.name, "picture_url": user.picture_url},
        headers={"authorization": f"Bearer {user.identifier}"},
    )
    return resp.json()


def started_game(test_client: TestClient) -> dict[str, Any]:
    """Get a started game waiting for the first move"""
    created_lobby = lobby_game(test_client)
    organizer = created_lobby["organizer"]["identifier"]
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
        f"/players/{active_player['identifier']}/games/{game['id']}/leave",
        headers={"authorization": f"Bearer {active_player['identifier']}"},
    )
    return resp.json()


def request_suggestion(test_client: TestClient, game_id: str, user: str = DEFAULT_ID):
    """get the suggestion for the game"""
    return test_client.get(
        f"/players/{user}/games/{game_id}/suggestion",
        headers={"authorization": f"Bearer {user}"},
    )


def get_suggestion(test_client: TestClient, game_id: str) -> dict[str, Any]:
    """get the suggestion for the game"""
    resp = request_suggestion(test_client, game_id)
    return resp.json()
