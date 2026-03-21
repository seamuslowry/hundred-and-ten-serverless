""" "Unit tests to ensure games that are in progress behave as expected"""

from fastapi.testclient import TestClient

from src.main.models.internal import BidAmount
from src.tests.helpers import (
    DEFAULT_ID,
    lobby_game,
    started_game,
)


def test_queue_bid_action(client: TestClient):
    """A non-active player can queue a bid"""
    lobby = lobby_game(client)

    manual_player = "manual-player"

    client.post(
        f"/players/{manual_player}/lobbies/{lobby['id']}/join",
        headers={"authorization": f"Bearer {manual_player}"},
    )
    game = client.post(
        f"/players/{DEFAULT_ID}/lobbies/{lobby['id']}/start",
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    ).json()

    # pre-bid on dealer; ensure take bid
    resp = client.post(
        f"/players/{DEFAULT_ID}/games/{game['id']}/queued-action",
        json={"type": "BID", "amount": BidAmount.SHOOT_THE_MOON},
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    )
    game = resp.json()
    player = next(p for p in game["players"] if p["id"] == DEFAULT_ID)
    assert "queued_action" in player and player["queued_action"] == {
        "type": "BID",
        "amount": BidAmount.SHOOT_THE_MOON,
        "player_id": DEFAULT_ID,
    }
    assert game["round"]["active_player"]["id"] == manual_player

    # bid as manual player
    resp = client.post(
        f"/players/{manual_player}/games/{game['id']}/act",
        json={"type": "BID", "amount": BidAmount.PASS},
        headers={"authorization": f"Bearer {manual_player}"},
    )
    game = resp.json()
    assert game["round"]["active_player"]["id"] == DEFAULT_ID
    assert game["status"] == "TRUMP_SELECTION"
    assert {
        "type": "BID",
        "player_id": DEFAULT_ID,
        "amount": BidAmount.SHOOT_THE_MOON,
    } in game["results"]
    player = next(p for p in game["players"] if p["id"] == DEFAULT_ID)
    assert "queued_action" in player and player["queued_action"] is None


def test_queue_pass_action(client: TestClient):
    """A non-active player can queue a bid"""
    lobby = lobby_game(client)

    manual_player = "manual-player"

    client.post(
        f"/players/{manual_player}/lobbies/{lobby['id']}/join",
        headers={"authorization": f"Bearer {manual_player}"},
    )
    game = client.post(
        f"/players/{DEFAULT_ID}/lobbies/{lobby['id']}/start",
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    ).json()

    # pre-pass on dealer
    resp = client.post(
        f"/players/{DEFAULT_ID}/games/{game['id']}/queued-action",
        json={"type": "BID", "amount": BidAmount.PASS},
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    )
    game = resp.json()
    player = next(p for p in game["players"] if p["id"] == DEFAULT_ID)
    assert "queued_action" in player and player["queued_action"] == {
        "type": "BID",
        "amount": BidAmount.PASS,
        "player_id": DEFAULT_ID,
    }
    assert game["round"]["active_player"]["id"] == manual_player

    # bid as manual player
    resp = client.post(
        f"/players/{manual_player}/games/{game['id']}/act",
        json={"type": "BID", "amount": BidAmount.PASS},
        headers={"authorization": f"Bearer {manual_player}"},
    )
    game = resp.json()
    assert {
        "type": "BID",
        "player_id": DEFAULT_ID,
        "amount": BidAmount.PASS,
    } in game["results"]
    player = next(p for p in game["players"] if p["id"] == DEFAULT_ID)
    assert "queued_action" in player and player["queued_action"] is None


def test_only_human_players(client: TestClient):
    """An automated player cannot queue an action"""
    game = started_game(client)

    # attempt queue action on automated player
    resp = client.post(
        f"/players/{game['players'][-1]['id']}/games/{game['id']}/queued-action",
        json={"type": "BID", "amount": BidAmount.SHOOT_THE_MOON},
        headers={"authorization": f"Bearer {game['players'][-1]['id']}"},
    )
    assert 400 == resp.status_code
