""" "Unit tests to ensure games that are in progress behave as expected"""

from fastapi.testclient import TestClient

from src.main.models.internal import BidAmount, RoundStatus
from src.tests.helpers import (
    DEFAULT_ID,
    contains_unsequenced,
    game_with_manual_player,
    get_game,
    get_suggestion,
    queue_action,
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
        f"/players/{DEFAULT_ID}/games/{created_game['id']}/actions",
        json={"type": "BID", "amount": BidAmount.SHOOT_THE_MOON},
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    )
    results = resp.json()

    # assert bid event in results
    contains_unsequenced(
        results,
        {
            "type": "BID",
            "player_id": DEFAULT_ID,
            "amount": BidAmount.SHOOT_THE_MOON,
        },
    )

    # assert that now in trump selection
    game = get_game(client, created_game["id"], DEFAULT_ID)
    assert RoundStatus.TRUMP_SELECTION.name == game["status"]

    # assert that current suggestion is a trump selection
    suggested_trump = get_suggestion(client, created_game["id"])
    assert "suit" in suggested_trump

    # select trump
    results = client.post(
        f"/players/{DEFAULT_ID}/games/{created_game['id']}/actions",
        json={"type": "SELECT_TRUMP", "suit": suggested_trump["suit"]},
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    ).json()

    # assert trump selection event in results
    contains_unsequenced(
        results,
        {
            "type": "SELECT_TRUMP",
            "player_id": DEFAULT_ID,
            "suit": suggested_trump["suit"],
        },
    )

    game = get_game(client, created_game["id"], DEFAULT_ID)
    assert RoundStatus.DISCARD.name == game["status"]

    # assert that current suggestion is a discard
    suggested_discard = get_suggestion(client, created_game["id"])
    assert "cards" in suggested_discard

    # discard
    results = client.post(
        f"/players/{DEFAULT_ID}/games/{created_game['id']}/actions",
        json={"type": "DISCARD", "cards": suggested_discard["cards"]},
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    ).json()

    # assert discard and trick start event in results
    contains_unsequenced(
        results,
        {
            "type": "DISCARD",
            "player_id": DEFAULT_ID,
            "cards": suggested_discard["cards"],
        },
    )
    contains_unsequenced(results, {"type": "TRICK_START"})

    game = get_game(client, created_game["id"], DEFAULT_ID)
    assert RoundStatus.TRICKS.name == game["status"]

    # ask for a suggestion so we know what card we can play
    suggested_play = get_suggestion(client, created_game["id"])
    assert "card" in suggested_play

    # play
    results = client.post(
        f"/players/{DEFAULT_ID}/games/{created_game['id']}/actions",
        json={"type": "PLAY", "card": suggested_play["card"]},
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    ).json()
    contains_unsequenced(
        results,
        {
            "type": "PLAY",
            "player_id": DEFAULT_ID,
            "card": suggested_play["card"],
        },
    )

    game = get_game(client, created_game["id"], DEFAULT_ID)
    assert RoundStatus.TRICKS.name == game["status"]
    assert 2 == len(game["round"]["tricks"])


def test_prepass_and_rescind_prepass(client: TestClient):
    """A non-active player can prepass and rescind that prepass"""
    game, _ = game_with_manual_player(client)

    # prepass
    queue_action(
        client, game["id"], DEFAULT_ID, {"type": "BID", "amount": BidAmount.PASS}
    )

    # rescind prepass
    results = client.delete(
        f"/players/{DEFAULT_ID}/games/{game['id']}/queued-actions",
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    ).json()
    assert len(results) == 0  # removing a queued action has no results
    game = get_game(client, game["id"], DEFAULT_ID)
    player = next(p for p in game["players"] if p["id"] == DEFAULT_ID)
    assert player["queued_actions"] == []


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
    results = client.post(
        f"/players/{active_player['id']}/games/{original_game['id']}/players",
        json={"type": "LEAVE"},
        headers={"authorization": f"Bearer {active_player['id']}"},
    ).json()

    # automates the organizer and ends the game
    assert any(r["type"] == "GAME_END" for r in results)

    game = get_game(client, original_game["id"], active_player["id"])
    active_player = next(p for p in game["players"] if p["id"] == active_player["id"])

    assert active_player["automate"]


def test_leave_playing_game_as_player(client: TestClient):
    """A player can leave an active game by automating themselves"""
    game, player = game_with_manual_player(client)
    non_organizer_player = next(p for p in game["players"] if p["id"] == player)
    assert non_organizer_player
    assert not non_organizer_player["automate"]

    # leave
    results = client.post(
        f"/players/{non_organizer_player['id']}/games/{game['id']}/players",
        json={"type": "LEAVE"},
        headers={"authorization": f"Bearer {non_organizer_player['id']}"},
    ).json()
    assert any(
        r["player_id"] == non_organizer_player["id"] for r in results
    )  # leaving makes them take a turn
    game = get_game(client, game["id"], non_organizer_player["id"])
    non_organizer_player = next(
        p for p in game["players"] if p["id"] == non_organizer_player["id"]
    )

    assert non_organizer_player["automate"]


def test_kick_player_as_organizer(client: TestClient):
    """An organizer can kick a player"""
    game, non_organizer_player = game_with_manual_player(client)

    # kick
    results = client.post(
        f"/players/{DEFAULT_ID}/games/{game['id']}/players",
        json={"type": "KICK", "player_id": non_organizer_player},
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    ).json()
    assert any(
        r["player_id"] == non_organizer_player for r in results
    )  # leaving makes them take a turn
    game = get_game(client, game["id"], non_organizer_player)
    assert next(p for p in game["players"] if p["id"] == non_organizer_player)[
        "automate"
    ]


def test_kick_player_as_player(client: TestClient):
    """A player cannot kick another player"""
    game, non_organizer_player = game_with_manual_player(client)

    # try kick
    resp = client.post(
        f"/players/{non_organizer_player}/games/{game['id']}/players",
        json={"type": "KICK", "player_id": DEFAULT_ID},
        headers={"authorization": f"Bearer {non_organizer_player}"},
    )
    assert 403 == resp.status_code
