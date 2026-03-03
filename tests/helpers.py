"""Helpers to perform common functions during testing"""

from typing import Any

from fastapi.testclient import TestClient

from function_app import fastapi_app
from utils import models

DEFAULT_ID = "id"


def get_client() -> TestClient:
    """Get a TestClient for the FastAPI app"""
    return TestClient(fastapi_app)


def lobby_game(
    organizer: str = DEFAULT_ID,
) -> dict[str, Any]:
    """Get a lobby waiting for the players"""
    client = get_client()
    resp = client.post(
        "/create",
        json={"name": "test game"},
        headers={"authorization": f"Bearer {organizer}"},
    )
    return resp.json()


def create_user(identifier: str, name: str = "") -> dict[str, Any]:
    """Attempt to create a user for the first time"""
    return __user("POST", models.User(identifier=identifier, name=name))


def update_user(identifier: str, name: str = "") -> dict[str, Any]:
    """Update an existing user if possible"""
    return __user("PUT", models.User(identifier=identifier, name=name))


def __user(method: str, user: models.User) -> dict[str, Any]:
    """Update an existing user if possible"""
    client = get_client()
    resp = client.request(
        method,
        "/self",
        json={"name": user.name, "picture_url": user.picture_url},
        headers={"authorization": f"Bearer {user.identifier}"},
    )
    return resp.json()


def started_game() -> dict[str, Any]:
    """Get a started game waiting for the first move"""
    client = get_client()
    created_lobby = lobby_game()
    resp = client.post(
        f"/start/{created_lobby['id']}",
        headers={"authorization": f"Bearer {created_lobby['organizer']['identifier']}"},
    )
    return resp.json()


def completed_game() -> dict[str, Any]:
    """Get a completed game"""
    client = get_client()
    game = started_game()

    active_player = game["round"]["active_player"]
    assert active_player

    resp = client.post(
        f"/leave/game/{game['id']}",
        headers={"authorization": f"Bearer {active_player['identifier']}"},
    )
    return resp.json()


def request_suggestion(game_id: str, user: str = DEFAULT_ID):
    """get the suggestion for the game"""
    client = get_client()
    return client.get(
        f"/suggestion/{game_id}",
        headers={"authorization": f"Bearer {user}"},
    )


def get_suggestion(game_id: str) -> dict[str, Any]:
    """get the suggestion for the game"""
    resp = request_suggestion(game_id)
    return resp.json()
