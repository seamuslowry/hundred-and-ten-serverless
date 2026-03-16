""" "Unit tests to ensure games that are in progress behave as expected"""

from fastapi.testclient import TestClient

from src.main.models.internal import BidAmount, RoundStatus, SelectableSuit
from src.tests.helpers import (
    DEFAULT_ID,
    get_suggestion,
    lobby_game,
    started_game,
)


def test_perform_round_actions(client: TestClient):
    """A round of the game can be played"""
    created_game = started_game(client)
    assert RoundStatus.BIDDING.name == created_game["status"]

    # assert that current suggestion is a bid
    suggested_bid = get_suggestion(client, created_game["id"])
    assert "amount" in suggested_bid

    # bid
    resp = client.post(
        f"/players/{DEFAULT_ID}/games/{created_game['id']}/bid",
        json={"amount": BidAmount.SHOOT_THE_MOON},
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    )
    game = resp.json()

    assert RoundStatus.TRUMP_SELECTION.name == game["status"]

    # assert that current suggestion is a trump selection
    suggested_trump = get_suggestion(client, created_game["id"])
    assert "suit" in suggested_trump

    # select trump
    resp = client.post(
        f"/players/{DEFAULT_ID}/games/{created_game['id']}/select",
        json={"suit": SelectableSuit.CLUBS.name},
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    )
    game = resp.json()

    print(game)

    assert RoundStatus.DISCARD.name == game["status"]

    # assert that current suggestion is a discard
    suggested_discard = get_suggestion(client, created_game["id"])
    assert "cards" in suggested_discard

    # discard
    resp = client.post(
        f"/players/{DEFAULT_ID}/games/{created_game['id']}/discard",
        json={"cards": []},
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    )
    game = resp.json()

    assert RoundStatus.TRICKS.name == game["status"]

    # ask for a suggestion so we know what card we can play
    suggested_play = get_suggestion(client, created_game["id"])
    assert "card" in suggested_play

    # play
    resp = client.post(
        f"/players/{DEFAULT_ID}/games/{created_game['id']}/play",
        json={"card": suggested_play["card"]},
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    )
    game = resp.json()

    assert RoundStatus.TRICKS.name == game["status"]
    assert 2 == len(game["round"]["tricks"])


def test_prepass_and_rescind_prepass(client: TestClient):
    """A non-active player can prepass and rescind that prepass"""
    game = started_game(client)

    non_active_player = next(
        p
        for p in game["round"]["players"]
        if game["round"]["active_player"]
        and p["id"] != game["round"]["active_player"]["id"]
    )

    # prepass
    resp = client.post(
        f"/players/{non_active_player['id']}/games/{game['id']}/bid",
        json={"amount": BidAmount.PASS},
        headers={"authorization": f"Bearer {non_active_player['id']}"},
    )
    game = resp.json()
    non_active_player = next(
        p for p in game["round"]["players"] if p["id"] == non_active_player["id"]
    )
    assert "prepassed" in non_active_player and non_active_player["prepassed"]

    # rescind prepass
    resp = client.post(
        f"/players/{non_active_player['id']}/games/{game['id']}/unpass",
        headers={"authorization": f"Bearer {non_active_player['id']}"},
    )
    game = resp.json()
    non_active_player = next(
        p for p in game["round"]["players"] if p["id"] == non_active_player["id"]
    )
    assert "prepassed" in non_active_player and not non_active_player["prepassed"]


def test_leave_playing_game_as_organizer(client: TestClient):
    """A player can leave an active game by automating themselves"""
    original_game = started_game(client)
    active_round_player = original_game["round"]["active_player"]
    active_player = next(
        p for p in original_game["players"] if p["id"] == active_round_player["id"]
    )
    assert active_player
    assert not active_player["automate"]

    # leave
    resp = client.post(
        f"/players/{DEFAULT_ID}/games/{original_game['id']}/leave",
        headers={"authorization": f"Bearer {active_player['id']}"},
    )
    game = resp.json()
    active_player = next(p for p in game["players"] if p["id"] == active_player["id"])

    assert active_player["automate"]


def test_leave_playing_game_as_player(client: TestClient):
    """A player can leave an active game by automating themselves"""
    lobby = lobby_game(client)
    player = "player"

    # join as player
    client.post(
        f"/players/{player}/lobbies/{lobby['id']}/join",
        headers={"authorization": f"Bearer {player}"},
    )

    # start the game
    resp = client.post(
        f"/players/{lobby['organizer']['id']}/lobbies/{lobby['id']}/start",
        headers={"authorization": f"Bearer {lobby['organizer']['id']}"},
    )

    game = resp.json()

    non_active_player = next(p for p in game["players"] if p["id"] == player)
    assert non_active_player
    assert not non_active_player["automate"]

    # leave
    resp = client.post(
        f"/players/{non_active_player['id']}/games/{game['id']}/leave",
        headers={"authorization": f"Bearer {non_active_player['id']}"},
    )
    game = resp.json()
    non_active_player = next(
        p for p in game["players"] if p["id"] == non_active_player["id"]
    )

    assert non_active_player["automate"]
