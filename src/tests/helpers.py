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
        f"/players/{organizer}/lobbies",
        json={"name": name},
        headers={"authorization": f"Bearer {organizer}"},
    )
    return resp.json()


def player(test_client: TestClient, upsert_player: Player) -> dict[str, Any]:
    """Upsert a existing player"""
    with patch(
        "src.main.auth.depends.verify_firebase_token",
        side_effect=lambda _: Identity(
            id=upsert_player.player_id,
            name=upsert_player.name or "",
            picture_url=upsert_player.picture_url,
        ),
    ):
        resp = test_client.put(
            f"/players/{upsert_player.player_id}",
            headers={"authorization": f"Bearer {upsert_player.player_id}"},
        )
    return resp.json()


def started_game(
    test_client: TestClient, organizer=DEFAULT_ID, name="test game"
) -> dict[str, Any]:
    """Get a started game waiting for the first move"""
    created_lobby = lobby_game(test_client, organizer=organizer, name=name)
    organizer = created_lobby["organizer"]["id"]
    results = test_client.post(
        f"/players/{organizer}/lobbies/{created_lobby['id']}/start",
        headers={"authorization": f"Bearer {organizer}"},
    ).json()
    assert {"type": "GAME_START", "sequence": 0} in results
    return get_game(test_client, created_lobby["id"], organizer)


def completed_game(test_client: TestClient) -> dict[str, Any]:
    """Get a completed game"""
    game = started_game(test_client)

    active_player_id = game["active_player_id"]
    assert active_player_id

    resp = test_client.post(
        f"/players/{active_player_id}/games/{game['id']}/players",
        json={"type": "LEAVE"},
        headers={"authorization": f"Bearer {active_player_id}"},
    )
    assert len(resp.json()) > 0
    return get_game(test_client, game["id"], active_player_id)


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


def game_with_manual_player(test_client: TestClient) -> tuple[dict[str, Any], str]:
    """Start a game with a manual player who has joined.

    Returns a tuple of (started_game, manual_player_id).
    The manual player can then take actions while DEFAULT_ID queues actions.
    """
    lobby = lobby_game(test_client)
    organizer = lobby["organizer"]["id"]
    manual_player = "manual-player"

    test_client.post(
        f"/players/{manual_player}/lobbies/{lobby['id']}/players",
        json={"type": "JOIN"},
        headers={"authorization": f"Bearer {manual_player}"},
    )
    resp = test_client.post(
        f"/players/{organizer}/lobbies/{lobby['id']}/start",
        headers={"authorization": f"Bearer {organizer}"},
    )
    assert 200 == resp.status_code
    return get_game(test_client, lobby["id"], organizer), manual_player


def queue_action(
    test_client: TestClient, game_id: str, player_id: str, action: dict[str, Any]
) -> dict[str, Any]:
    """Queue an action and return the response."""
    results = test_client.post(
        f"/players/{player_id}/games/{game_id}/queued-actions",
        json=action,
        headers={"authorization": f"Bearer {player_id}"},
    ).json()

    game = get_game(test_client, game_id, player_id)

    queued_player = next(p for p in game["players"] if p["id"] == player_id)
    contains_unsequenced(
        queued_player["queued_actions"][:-1],
        {
            **action,
            "player_id": DEFAULT_ID,
        },
    )

    return results


def get_game(test_client: TestClient, game_id: str, player_id: str) -> dict[str, Any]:
    """Get a game as the given player"""
    return test_client.get(
        f"/players/{player_id}/games/{game_id}",
        headers={"authorization": f"Bearer {player_id}"},
    ).json()


def contains_unsequenced(
    events: list[dict[str, Any]], unordered_event: dict[str, Any]
) -> bool:
    """Tests if an event without order context exists in the list"""
    ignore_keys = "sequence"
    return any(
        all(
            item.get(k) == v for k, v in unordered_event.items() if k not in ignore_keys
        )
        for item in events
    )
