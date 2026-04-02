"""Test to ensure game events are returned properly through the web server"""

from fastapi.testclient import TestClient

from main.models.internal.constants import BidAmount, CardSuit
from src.tests.helpers import (
    DEFAULT_ID,
    completed_game,
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
    assert events[0]["type"] == "GAME_START"
    assert events[0]["sequence"] == 0
    assert events[1]["type"] == "ROUND_START"
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

    assert game["status"] == "TRICKS"

    events_before = get_events(client, game["id"], DEFAULT_ID)
    assert events_before[-4]["type"] == "TRICK_START"  # automated plays after
    assert not any(e["type"] == "TRICK_END" for e in events_before)

    suggestion = get_suggestion(client, game["id"])
    assert suggestion["type"] == "PLAY"
    queue_action(client, game["id"], DEFAULT_ID, suggestion)

    events_after = get_events(client, game["id"], DEFAULT_ID)
    assert any(e["type"] == "TRICK_END" for e in events_after[-6:])


def test_partial_round(client: TestClient):
    """While round isn't over, no RoundEnd event exists"""
    game = started_game(client)
    events = get_events(client, game["id"], DEFAULT_ID)

    assert len(events) > 0
    assert not any(e["type"] == "ROUND_END" for e in events)


def test_completed_round(client: TestClient):
    """Once the round is over, it will have a RoundEnd event"""
    game = completed_game(client)
    events = get_events(client, game["id"], DEFAULT_ID)

    assert len(events) > 0
    assert any(e["type"] == "ROUND_END" for e in events)


def test_completed_game(client: TestClient):
    """Once the game is over, it will have a GameEnd event"""
    game = completed_game(client)

    assert game["status"] == "WON"

    events = get_events(client, game["id"], DEFAULT_ID)

    game_end_events = [e for e in events if e["type"] == "GAME_END"]
    assert len(game_end_events) >= 1
    assert events[-1]["type"] == "GAME_END"
