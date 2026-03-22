""" "Unit tests to ensure games that are in progress behave as expected"""

from fastapi.testclient import TestClient

from src.main.models.client.constants import SelectableSuit
from src.main.models.internal import BidAmount
from src.tests.helpers import (
    DEFAULT_ID,
    game_with_manual_player,
    get_game,
    queue_action,
    started_game,
)


def test_queue_bid_action(client: TestClient):
    """A non-active player can queue a bid"""
    game, manual_player = game_with_manual_player(client)
    assert game["round"]["active_player"]["id"] == manual_player

    # pre-bid on dealer; ensure take bid
    queue_action(
        client,
        game["id"],
        DEFAULT_ID,
        {"type": "BID", "amount": BidAmount.SHOOT_THE_MOON},
    )

    # bid as manual player
    results = client.post(
        f"/players/{manual_player}/games/{game['id']}/act",
        json={"type": "BID", "amount": BidAmount.PASS},
        headers={"authorization": f"Bearer {manual_player}"},
    ).json()

    assert {
        "type": "BID",
        "amount": BidAmount.SHOOT_THE_MOON,
        "player_id": DEFAULT_ID,
    } in results

    game = get_game(client, game["id"], manual_player)

    assert game["round"]["active_player"]["id"] == DEFAULT_ID
    assert game["status"] == "TRUMP_SELECTION"
    player = next(p for p in game["players"] if p["id"] == DEFAULT_ID)
    assert player["queued_actions"] == []


def test_queue_pass_action(client: TestClient):
    """A non-active player can queue a bid"""
    game, manual_player = game_with_manual_player(client)
    assert game["round"]["active_player"]["id"] == manual_player

    # pre-pass on dealer
    queue_action(
        client, game["id"], DEFAULT_ID, {"type": "BID", "amount": BidAmount.PASS}
    )

    # bid as manual player
    results = client.post(
        f"/players/{manual_player}/games/{game['id']}/act",
        json={"type": "BID", "amount": BidAmount.PASS},
        headers={"authorization": f"Bearer {manual_player}"},
    ).json()
    assert {
        "type": "BID",
        "player_id": DEFAULT_ID,
        "amount": BidAmount.PASS,
    } in results
    game = get_game(client, game["id"], manual_player)

    player = next(p for p in game["players"] if p["id"] == DEFAULT_ID)
    assert player["queued_actions"] == []


def test_only_human_players_queue(client: TestClient):
    """An automated player cannot queue an action"""
    game = started_game(client)

    # attempt queue action on automated player
    resp = client.post(
        f"/players/{game['players'][-1]['id']}/games/{game['id']}/queued-actions",
        json={"type": "BID", "amount": BidAmount.SHOOT_THE_MOON},
        headers={"authorization": f"Bearer {game['players'][-1]['id']}"},
    )
    assert 400 == resp.status_code


def test_only_human_players_clear_queue(client: TestClient):
    """An automated player cannot clear action queue"""
    game = started_game(client)

    # attempt clear queue action on automated player
    resp = client.delete(
        f"/players/{game['players'][-1]['id']}/games/{game['id']}/queued-actions",
        headers={"authorization": f"Bearer {game['players'][-1]['id']}"},
    )
    assert 400 == resp.status_code


def test_queue_multiple_actions(client: TestClient):
    """Multiple play actions can be queued and are played in FIFO order"""
    game, manual_player = game_with_manual_player(client)
    assert game["round"]["active_player"]["id"] == manual_player

    hand_resp = client.get(
        f"/players/{DEFAULT_ID}/games/{game['id']}",
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    )
    hand = hand_resp.json()["round"]["players"][0]["hand"]
    assert len(hand) >= 2, "Need at least 2 cards in hand"
    card1, card2 = hand[0], hand[1]

    # queue actions
    # dealer takes the bid to ensure we go into tricks
    queue_action(
        client,
        game["id"],
        DEFAULT_ID,
        {"type": "BID", "amount": BidAmount.SHOOT_THE_MOON},
    )
    # dealer selects DIAMONDS as trump
    queue_action(
        client,
        game["id"],
        DEFAULT_ID,
        {"type": "SELECT_TRUMP", "suit": SelectableSuit.DIAMONDS},
    )
    # dealer discards none
    queue_action(client, game["id"], DEFAULT_ID, {"type": "DISCARD", "cards": []})
    # dealer plays first card
    queue_action(client, game["id"], DEFAULT_ID, {"type": "PLAY", "card": card1})
    # delaer plays second card
    queue_action(client, game["id"], DEFAULT_ID, {"type": "PLAY", "card": card2})

    # manual player leaves to automate themselves
    results = client.post(
        f"/players/{manual_player}/games/{game['id']}/leave",
        headers={"authorization": f"Bearer {manual_player}"},
    ).json()

    # the final play action is in the results
    assert {"type": "PLAY", "player_id": DEFAULT_ID, "card": card2} in results

    # queued actions are consumed
    game = get_game(client, game["id"], manual_player)
    player = next(p for p in game["players"] if p["id"] == DEFAULT_ID)
    assert len(player["queued_actions"]) == 0
