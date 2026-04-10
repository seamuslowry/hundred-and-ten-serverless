"""Unit tests to ensure games that are in progress behave as expected"""

from fastapi.testclient import TestClient

from src.models.client.constants import SelectableSuit
from src.models.internal import BidAmount
from tests.helpers import (
    DEFAULT_ID,
    contains_unsequenced,
    game_with_manual_player,
    get_game,
    queue_action,
    started_game,
)


def test_queue_bid_action(client: TestClient):
    """A non-active player can queue a bid"""
    game, manual_player = game_with_manual_player(client)
    assert game["active_player_id"] == manual_player

    # pre-bid on dealer; ensure take bid
    queue_action(
        client,
        game["id"],
        DEFAULT_ID,
        {"type": "BID", "amount": BidAmount.SHOOT_THE_MOON},
    )

    # bid as manual player
    results = client.post(
        f"/players/{manual_player}/games/{game['id']}/actions",
        json={"type": "BID", "amount": BidAmount.PASS},
        headers={"authorization": f"Bearer {manual_player}"},
    ).json()

    contains_unsequenced(
        results,
        {
            "player_id": DEFAULT_ID,
            "type": "BID",
            "amount": BidAmount.SHOOT_THE_MOON,
        },
    )

    game = get_game(client, game["id"], DEFAULT_ID)

    assert game["active_player_id"] == DEFAULT_ID
    assert game["status"] == "TRUMP_SELECTION"
    player = next(p for p in game["players"] if p["id"] == DEFAULT_ID)
    assert player["queued_actions"] == []


def test_queue_pass_action(client: TestClient):
    """A non-active player can queue a bid"""
    game, manual_player = game_with_manual_player(client)
    assert game["active_player_id"] == manual_player

    # pre-pass on dealer
    queue_action(client, game["id"], DEFAULT_ID, {"type": "BID", "amount": BidAmount.PASS})

    # bid as manual player
    results = client.post(
        f"/players/{manual_player}/games/{game['id']}/actions",
        json={"type": "BID", "amount": BidAmount.PASS},
        headers={"authorization": f"Bearer {manual_player}"},
    ).json()

    contains_unsequenced(
        results,
        {
            "type": "BID",
            "player_id": DEFAULT_ID,
            "amount": BidAmount.PASS,
        },
    )

    game = get_game(client, game["id"], DEFAULT_ID)

    player = next(p for p in game["players"] if p["id"] == DEFAULT_ID)
    assert player["queued_actions"] == []


def test_other_players_cant_see_queue(client: TestClient):
    """Players can't see other players' queued actions"""
    game, manual_player = game_with_manual_player(client)
    assert game["active_player_id"] == manual_player

    # pre-pass as default
    queue_action(client, game["id"], DEFAULT_ID, {"type": "BID", "amount": BidAmount.PASS})

    manual_player_view = get_game(client, game["id"], manual_player)
    player = next(p for p in manual_player_view["players"] if p["id"] == DEFAULT_ID)
    assert "queued_actions" not in player

    default_player_view = get_game(client, game["id"], DEFAULT_ID)
    player = next(p for p in default_player_view["players"] if p["id"] == DEFAULT_ID)
    assert "queued_actions" in player


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
    assert game["active_player_id"] == manual_player

    hand_resp = client.get(
        f"/players/{DEFAULT_ID}/games/{game['id']}",
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    )
    hand = hand_resp.json()["players"][0]["hand"]
    card = next(c for c in hand if c["suit"] != "JOKER")

    # queue actions
    # dealer takes the bid to ensure we go into tricks
    queue_action(
        client,
        game["id"],
        DEFAULT_ID,
        {"type": "BID", "amount": BidAmount.SHOOT_THE_MOON},
    )
    # dealer selects cart suit as trump
    queue_action(
        client,
        game["id"],
        DEFAULT_ID,
        {"type": "SELECT_TRUMP", "suit": card["suit"]},
    )
    # dealer discards none
    queue_action(client, game["id"], DEFAULT_ID, {"type": "DISCARD", "cards": []})
    # dealer plays card
    queue_action(client, game["id"], DEFAULT_ID, {"type": "PLAY", "card": card})

    # manual player leaves to automate themselves
    results = client.post(
        f"/players/{manual_player}/games/{game['id']}/players",
        json={"type": "LEAVE"},
        headers={"authorization": f"Bearer {manual_player}"},
    ).json()

    # the final play action is in the results
    contains_unsequenced(
        results,
        {
            "type": "PLAY",
            "card": card,
            "player_id": DEFAULT_ID,
        },
    )

    # queued actions are consumed
    game = get_game(client, game["id"], DEFAULT_ID)
    player = next(p for p in game["players"] if p["id"] == DEFAULT_ID)
    assert len(player["queued_actions"]) == 0


def test_invalid_action_clears_queue(client: TestClient):
    """An invalid queued action clears the entire queue on the player's turn"""
    game, manual_player = game_with_manual_player(client)
    assert game["active_player_id"] == manual_player

    # queue a bid of FIFTEEN and a select trump of DIAMONDS
    queue_action(client, game["id"], DEFAULT_ID, {"type": "BID", "amount": BidAmount.FIFTEEN})
    queue_action(
        client,
        game["id"],
        DEFAULT_ID,
        {"type": "SELECT_TRUMP", "suit": SelectableSuit.DIAMONDS},
    )

    # manual player bids higher; queued actions are checked against new game state
    results = client.post(
        f"/players/{manual_player}/games/{game['id']}/actions",
        json={"type": "BID", "amount": BidAmount.SHOOT_THE_MOON},
        headers={"authorization": f"Bearer {manual_player}"},
    ).json()

    assert not any(a["player_id"] == DEFAULT_ID for a in results)

    # FIFTEEN is below 60 (not in available_actions), dropped. SELECT_TRUMP is not
    # valid during BIDDING, also dropped. The FIFO drain clears the entire queue.
    game = get_game(client, game["id"], DEFAULT_ID)
    assert game["status"] == "BIDDING"
    assert game["active_player_id"] == DEFAULT_ID
    player = next(p for p in game["players"] if p["id"] == DEFAULT_ID)
    assert player["queued_actions"] == []


def test_valid_queued_action_survives_other_players_turns(client: TestClient):
    """A valid queued action stays queued through other players' turns"""
    game, manual_player = game_with_manual_player(client)
    assert game["active_player_id"] == manual_player

    # queue a bid of SHOOT_THE_MOON and select trump of DIAMONDS
    queue_action(
        client,
        game["id"],
        DEFAULT_ID,
        {"type": "BID", "amount": BidAmount.SHOOT_THE_MOON},
    )
    queue_action(
        client,
        game["id"],
        DEFAULT_ID,
        {"type": "SELECT_TRUMP", "suit": SelectableSuit.DIAMONDS},
    )

    # manual player bids FIFTEEN
    results = client.post(
        f"/players/{manual_player}/games/{game['id']}/actions",
        json={"type": "BID", "amount": BidAmount.FIFTEEN},
        headers={"authorization": f"Bearer {manual_player}"},
    ).json()

    # DEFAULT_ID's SHOOT_THE_MOON was consumed and appears in results

    contains_unsequenced(
        results,
        {
            "amount": BidAmount.SHOOT_THE_MOON,
            "type": "BID",
            "player_id": DEFAULT_ID,
        },
    )

    # The queued SHOOT_THE_MOON is consumed (valid); SELECT_TRUMP is then checked
    # against available_actions during BIDDING and is not valid, so it is dropped.
    # SELECT_TRUMP survives in the queue since it was not the action consumed.
    game = get_game(client, game["id"], DEFAULT_ID)
    assert game["status"] == "BIDDING"
    player = next(p for p in game["players"] if p["id"] == DEFAULT_ID)
    assert contains_unsequenced(
        player["queued_actions"],
        {
            "type": "SELECT_TRUMP",
            "player_id": DEFAULT_ID,
            "suit": SelectableSuit.DIAMONDS,
        },
    )
