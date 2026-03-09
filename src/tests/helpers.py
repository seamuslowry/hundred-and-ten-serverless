"""Helpers to perform common functions during testing"""

import atexit
from contextlib import ExitStack
from typing import Any, cast

from fastapi.testclient import TestClient

from function_app import fastapi_app
from src.main.models.internal import User

DEFAULT_ID = "id"
_STATE: dict[str, Any] = {"stack": ExitStack(), "client": None}


def get_client() -> TestClient:
    """Get a TestClient for the FastAPI app"""
    client = _STATE["client"]
    if client is None:
        _STATE["client"] = _STATE["stack"].enter_context(TestClient(fastapi_app))
        client = _STATE["client"]

    return cast(TestClient, client)


def _reset_client() -> None:
    _STATE["stack"].close()
    _STATE["stack"] = ExitStack()
    _STATE["client"] = None


@atexit.register
def _close_client() -> None:
    _STATE["stack"].close()


def lobby_game(
    organizer: str = DEFAULT_ID,
) -> dict[str, Any]:
    """Get a lobby waiting for the players"""
    client = get_client()
    resp = client.post(
        f"/players/{organizer}/lobbies/create",
        json={"name": "test game"},
        headers={"authorization": f"Bearer {organizer}"},
    )
    return resp.json()


def create_user(identifier: str, name: str = "") -> dict[str, Any]:
    """Attempt to create a user for the first time"""
    return __user("POST", User(identifier=identifier, name=name))


def update_user(identifier: str, name: str = "") -> dict[str, Any]:
    """Update an existing user if possible"""
    return __user("PUT", User(identifier=identifier, name=name))


def __user(method: str, user: User) -> dict[str, Any]:
    """Update an existing user if possible"""
    client = get_client()
    resp = client.request(
        method,
        f"/players/{user.identifier}",
        json={"name": user.name, "picture_url": user.picture_url},
        headers={"authorization": f"Bearer {user.identifier}"},
    )
    return resp.json()


def started_game() -> dict[str, Any]:
    """Get a started game waiting for the first move"""
    client = get_client()
    created_lobby = lobby_game()
    organizer = created_lobby["organizer"]["identifier"]
    resp = client.post(
        f"/players/{organizer}/lobbies/{created_lobby['id']}/start",
        headers={"authorization": f"Bearer {organizer}"},
    )
    return resp.json()


def completed_game() -> dict[str, Any]:
    """Get a completed game"""
    client = get_client()
    game = started_game()

    active_player = game["round"]["active_player"]
    assert active_player

    resp = client.post(
        f"/players/{active_player['identifier']}/games/{game['id']}/leave",
        headers={"authorization": f"Bearer {active_player['identifier']}"},
    )
    return resp.json()


def request_suggestion(game_id: str, user: str = DEFAULT_ID):
    """get the suggestion for the game"""
    client = get_client()
    return client.get(
        f"/players/{user}/games/{game_id}/suggestion",
        headers={"authorization": f"Bearer {user}"},
    )


def get_suggestion(game_id: str) -> dict[str, Any]:
    """get the suggestion for the game"""
    resp = request_suggestion(game_id)
    return resp.json()
