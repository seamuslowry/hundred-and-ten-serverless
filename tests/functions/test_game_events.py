"""Test to ensure game events are returned properly through the web server"""

from fastapi.testclient import TestClient

from src.models.internal.constants import BidAmount, CardSuit
from tests.helpers import (
    DEFAULT_ID,
    completed_game,
    game_with_manual_player,
    get_events,
    get_game,
    get_suggestion,
    queue_action,
    started_game,
)


def test_new_game(client: TestClient):
    """Before any plays, just the game start event exists"""
    game = started_game(client)
    events = get_events(client, game["id"], DEFAULT_ID)

    assert len(events) >= 2
    assert events[0]["content"]["type"] == "GAME_START"
    assert events[0]["sequence"] == 0
    assert events[1]["content"]["type"] == "ROUND_START"
    assert events[1]["sequence"] == 1


def test_partial_trick(client: TestClient):
    """While round isn't over, no TrickEnd event exists"""
    game = started_game(client)

    queue_action(
        client,
        game["id"],
        DEFAULT_ID,
        {"amount": BidAmount.SHOOT_THE_MOON, "type": "BID"},
    )
    queue_action(
        client,
        game["id"],
        DEFAULT_ID,
        {"type": "SELECT_TRUMP", "suit": CardSuit.DIAMONDS},
    )
    queue_action(client, game["id"], DEFAULT_ID, {"type": "DISCARD", "cards": []})

    game = get_game(client, game["id"], DEFAULT_ID)

    assert game["active"]["status"] == "TRICKS"

    events_before = get_events(client, game["id"], DEFAULT_ID)
    assert (
        events_before[-4]["content"]["type"] == "TRICK_START"
    )  # automated plays after
    assert not any(e["content"]["type"] == "TRICK_END" for e in events_before)

    suggestion = get_suggestion(client, game["id"])
    assert suggestion["type"] == "PLAY"
    queue_action(client, game["id"], DEFAULT_ID, suggestion)

    events_after = get_events(client, game["id"], DEFAULT_ID)
    assert any(e["content"]["type"] == "TRICK_END" for e in events_after[-6:])


def test_partial_round(client: TestClient):
    """While round isn't over, no RoundEnd event exists"""
    game = started_game(client)
    events = get_events(client, game["id"], DEFAULT_ID)

    assert len(events) > 0
    assert not any(e["content"]["type"] == "ROUND_END" for e in events)


def test_completed_round(client: TestClient):
    """Once the round is over, it will have a RoundEnd event"""
    game = completed_game(client)
    events = get_events(client, game["id"], DEFAULT_ID)

    assert len(events) > 0
    assert any(e["content"]["type"] == "ROUND_END" for e in events)


def test_completed_game(client: TestClient):
    """Once the game is over, it will have a GameEnd event"""
    game = completed_game(client)

    assert game["active"]["status"] == "WON"

    events = get_events(client, game["id"], DEFAULT_ID)

    game_end_events = [e for e in events if e["content"]["type"] == "GAME_END"]
    assert len(game_end_events) >= 1
    assert events[-1]["content"]["type"] == "GAME_END"


def test_round_start_has_own_hand(client: TestClient):
    """RoundStart event includes the requesting player's dealt cards"""
    game = started_game(client)
    events = get_events(client, game["id"], DEFAULT_ID)

    round_start = next(
        e["content"] for e in events if e["content"]["type"] == "ROUND_START"
    )
    hands = round_start["hands"]

    # Own player sees a list of card objects
    assert isinstance(hands[DEFAULT_ID], list)
    assert len(hands[DEFAULT_ID]) == 5
    for card in hands[DEFAULT_ID]:
        assert "suit" in card
        assert "number" in card


def test_round_start_has_opponent_counts(client: TestClient):
    """RoundStart event shows opponent hand sizes as integers"""
    game = started_game(client)
    events = get_events(client, game["id"], DEFAULT_ID)

    round_start = next(
        e["content"] for e in events if e["content"]["type"] == "ROUND_START"
    )
    hands = round_start["hands"]

    # Other players see integer counts
    opponent_ids = [pid for pid in hands if pid != DEFAULT_ID]
    assert len(opponent_ids) > 0
    for opponent_id in opponent_ids:
        assert hands[opponent_id] == 5


def test_round_start_visibility_per_player(client: TestClient):
    """Each player sees their own cards and opponents' counts"""
    game, manual_player = game_with_manual_player(client)

    events_organizer = get_events(client, game["id"], DEFAULT_ID)
    events_manual = get_events(client, game["id"], manual_player)

    rs_organizer = next(
        e["content"] for e in events_organizer if e["content"]["type"] == "ROUND_START"
    )
    rs_manual = next(
        e["content"] for e in events_manual if e["content"]["type"] == "ROUND_START"
    )

    # Organizer sees own cards as list, manual player as int
    assert isinstance(rs_organizer["hands"][DEFAULT_ID], list)
    assert isinstance(rs_organizer["hands"][manual_player], int)

    # Manual player sees own cards as list, organizer as int
    assert isinstance(rs_manual["hands"][manual_player], list)
    assert isinstance(rs_manual["hands"][DEFAULT_ID], int)


def test_completed_game_round_start_hands(client: TestClient):
    """Completed game events include hands on RoundStart"""
    game = completed_game(client)
    events = get_events(client, game["id"], DEFAULT_ID)

    round_starts = [
        e["content"] for e in events if e["content"]["type"] == "ROUND_START"
    ]
    assert len(round_starts) >= 1

    for rs in round_starts:
        assert "hands" in rs
        assert len(rs["hands"]) > 0
