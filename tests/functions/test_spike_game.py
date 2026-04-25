"""Integration tests for the spike game read endpoint"""

from fastapi.testclient import TestClient

from src.models.internal.constants import BidAmount, CardSuit
from tests.helpers import (
    DEFAULT_ID,
    completed_game,
    game_with_manual_player,
    get_spike_game,
    queue_action,
    started_game,
)

# ---------------------------------------------------------------------------
# New game
# ---------------------------------------------------------------------------


def test_new_game_single_active_bidding_round(client: TestClient):
    """New game has no completed rounds and an active BIDDING round."""
    game = started_game(client)
    spike = get_spike_game(client, game["id"], DEFAULT_ID)

    assert spike["active"]["status"] == "BIDDING"
    assert spike["completed_rounds"] == []
    active = spike["active"]
    assert active["trump"] is None
    assert active["tricks"] == []
    assert active["discards"] == {}


# ---------------------------------------------------------------------------
# Completed game
# ---------------------------------------------------------------------------


def test_completed_game_top_level_fields(client: TestClient):
    """Completed game has active.status WON and a winner_player_id."""
    game = completed_game(client)
    spike = get_spike_game(client, game["id"], DEFAULT_ID)

    assert spike["active"]["status"] == "WON"
    assert spike["active"]["winner_player_id"] is not None
    assert spike["id"] == game["id"]
    assert spike["name"] == game["name"]
    assert len(spike["players"]) == 4
    assert isinstance(spike["scores"], dict)


def test_completed_game_all_rounds_have_status(client: TestClient):
    """All completed_rounds in a finished game are COMPLETED or COMPLETED_NO_BIDDERS."""
    game = completed_game(client)
    spike = get_spike_game(client, game["id"], DEFAULT_ID)

    for game_round in spike["completed_rounds"]:
        assert game_round["status"] in (
            "COMPLETED",
            "COMPLETED_NO_BIDDERS",
        ), f"Unexpected round status: {game_round['status']}"


def test_completed_rounds_show_full_info(client: TestClient):
    """Completed rounds shows full info."""
    game = completed_game(client)
    spike = get_spike_game(client, game["id"], DEFAULT_ID)

    for game_round in spike["completed_rounds"]:
        assert len(game_round["initial_hands"].keys()) == 4
        for player_id, hand in game_round["initial_hands"].items():
            assert isinstance(
                hand, list
            ), f"Player {player_id} hand should be a card list in completed round"
        if game_round["status"] == "COMPLETED":
            for player_id, discards in game_round["discards"].items():
                assert isinstance(
                    discards["discarded"], list
                ), f"Player {player_id} should show discards in a completed round"
                assert isinstance(
                    discards["received"], list
                ), f"Player {player_id} should show received cards in completed round"

                assert len(discards["discarded"]) == len(discards["received"])


def test_completed_rounds_show_tricks_with_bleeding(client: TestClient):
    """Completed rounds include trick information."""
    game = completed_game(client)
    spike = get_spike_game(client, game["id"], DEFAULT_ID)

    for game_round in spike["completed_rounds"]:
        if game_round["status"] == "COMPLETED":
            assert len(game_round["tricks"]) == 5
            for trick in game_round["tricks"]:
                assert "bleeding" in trick
                assert isinstance(trick["bleeding"], bool)
                assert trick["winning_play"] is not None


def test_all_pass_rounds_have_hands_but_no_tricks(client: TestClient):
    """COMPLETED_NO_BIDDERS rounds have initial_hands but no tricks or discards."""

    no_bidders_rounds = []

    # be sure that the game has COMPLETED_NO_BIDDERS to avoid flake
    while not no_bidders_rounds:
        game = completed_game(client)
        spike = get_spike_game(client, game["id"], DEFAULT_ID)

        no_bidders_rounds = [
            r
            for r in spike["completed_rounds"]
            if r["status"] == "COMPLETED_NO_BIDDERS"
        ]

    for game_round in no_bidders_rounds:
        assert len(game_round["initial_hands"]) == 4
        # COMPLETED_NO_BIDDERS rounds only have: status, dealer_player_id, initial_hands
        assert set(game_round.keys()) == {
            "status",
            "dealer_player_id",
            "initial_hands",
        }
        break


def test_completed_game_scores_sum_to_cumulative(client: TestClient):
    """Sum of COMPLETED round scores equals top-level cumulative scores.
    COMPLETED_NO_BIDDERS rounds score 0 for all players and have no scores field.
    """
    game = completed_game(client)
    spike = get_spike_game(client, game["id"], DEFAULT_ID)

    total: dict[str, int] = {}
    for game_round in spike["completed_rounds"]:
        if game_round["status"] == "COMPLETED":
            for pid, v in game_round["scores"].items():
                total[pid] = total.get(pid, 0) + v

    for pid, expected in spike["scores"].items():
        assert (
            total.get(pid, 0) == expected
        ), f"Player {pid}: round score sum {total.get(pid, 0)} != cumulative {expected}"


# ---------------------------------------------------------------------------
# Completed game: de-anonymization is requester-independent
# ---------------------------------------------------------------------------


def test_two_players_see_identical_completed_round_data(client: TestClient):
    """Two different players see the same data for completed rounds."""
    game = completed_game(client)
    # The active_player_id before the game ended is stored in the game
    # Use two player IDs from the game's players list
    player_ids = [p["id"] for p in game["players"]]
    p1, p2 = player_ids[0], player_ids[1]

    spike_p1 = get_spike_game(client, game["id"], p1)
    spike_p2 = get_spike_game(client, game["id"], p2)

    assert spike_p1 == spike_p2


# ---------------------------------------------------------------------------
# Active round
# ---------------------------------------------------------------------------


def test_new_trick_no_winning_play(client: TestClient):
    """A trick with only has a winning play with >0 plays."""
    game, manual_player = game_with_manual_player(client)

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
        {"type": "SELECT_TRUMP", "suit": CardSuit.DIAMONDS},
    )
    queue_action(client, game["id"], DEFAULT_ID, {"type": "DISCARD", "cards": []})
    queue_action(
        client, game["id"], manual_player, {"type": "BID", "amount": BidAmount.PASS}
    )
    queue_action(client, game["id"], manual_player, {"type": "DISCARD", "cards": []})

    no_plays = get_spike_game(client, game["id"], manual_player)
    no_plays_round = no_plays["active"]
    assert no_plays_round["status"] == "TRICKS"
    assert len(no_plays_round["tricks"]) == 1
    assert len(no_plays_round["tricks"][0]["plays"]) == 0
    assert no_plays_round["tricks"][0]["winning_play"] is None

    queue_action(
        client,
        game["id"],
        manual_player,
        {"type": "PLAY", "card": no_plays["active"]["hands"][manual_player][0]},
    )

    one_play = get_spike_game(client, game["id"], manual_player)
    one_play_round = one_play["active"]
    assert one_play_round["status"] == "TRICKS"
    assert len(one_play_round["tricks"]) == 1
    assert len(one_play_round["tricks"][0]["plays"]) == 3  # manual and two automatic
    assert one_play_round["tricks"][0]["winning_play"] is not None


def test_active_round_self_sees_cards(client: TestClient):
    """Requesting player sees only their own hand as cards."""
    game = started_game(client)
    spike = get_spike_game(client, game["id"], DEFAULT_ID)

    active = spike["active"]
    assert active["status"] == "BIDDING"
    assert isinstance(active["hands"][DEFAULT_ID], list)
    assert len(active["hands"][DEFAULT_ID]) == 5
    for card in active["hands"][DEFAULT_ID]:
        assert "suit" in card
        assert "number" in card


def test_active_round_others_see_count(client: TestClient):
    """Other players' hands are integers in the active round."""
    game = started_game(client)
    spike = get_spike_game(client, game["id"], DEFAULT_ID)

    active = spike["active"]
    for pid, hand in active["hands"].items():
        if pid != DEFAULT_ID:
            assert isinstance(hand, int)
            assert hand == 5


def test_active_round_includes_active_player_id(client: TestClient):
    """Active round includes active_player_id."""
    game = started_game(client)
    spike = get_spike_game(client, game["id"], DEFAULT_ID)

    active = spike["active"]
    assert "active_player_id" in active
    assert active["active_player_id"] == game["active_player_id"]


def test_two_players_see_different_hands_in_active_round(client: TestClient):
    """Two players see each other's hands as counts."""
    game, manual_player = game_with_manual_player(client)

    spike_organizer = get_spike_game(client, game["id"], DEFAULT_ID)
    spike_manual = get_spike_game(client, game["id"], manual_player)

    active_org = spike_organizer["active"]
    active_man = spike_manual["active"]

    # Organizer sees own cards, manual player as count
    assert isinstance(active_org["hands"][DEFAULT_ID], list)
    assert isinstance(active_org["hands"][manual_player], int)

    # Manual player sees own cards, organizer as count
    assert isinstance(active_man["hands"][manual_player], list)
    assert isinstance(active_man["hands"][DEFAULT_ID], int)


def test_active_round_bid_is_none_before_any_bid(client: TestClient):
    """Active round bid field is null when no one has bid yet.

    Uses game_with_manual_player so the first active player is Human and no
    CPU automation fires before the first act, guaranteeing bid starts null.
    """
    game, _ = game_with_manual_player(client)
    spike = get_spike_game(client, game["id"], DEFAULT_ID)

    assert spike["active"]["bid"] is None


def test_active_round_bid_populated_after_a_bid(client: TestClient):
    """Active round bid field contains player_id and amount once a bid is placed."""
    game, manual_player = game_with_manual_player(client)
    assert game["active_player_id"] == manual_player

    queue_action(
        client, game["id"], manual_player, {"type": "BID", "amount": BidAmount.TWENTY}
    )

    spike = get_spike_game(client, game["id"], DEFAULT_ID)
    bid = spike["active"]["bid"]
    assert bid is not None
    assert bid["player_id"] == manual_player
    assert bid["amount"] == BidAmount.TWENTY


def test_active_round_queued_actions(client: TestClient):
    """Active round includes queued_actions field for the requesting player."""
    game, _ = game_with_manual_player(client)

    # Queue an action for DEFAULT_ID (organizer) when it may not be their turn
    queue_action(
        client,
        game["id"],
        DEFAULT_ID,
        {"amount": BidAmount.TWENTY, "type": "BID"},
    )

    spike = get_spike_game(client, game["id"], DEFAULT_ID)
    active = spike["active"]
    assert "queued_actions" in active
    # queued_actions may be empty if action was consumed; field presence is what matters
    assert isinstance(active["queued_actions"], list)


# ---------------------------------------------------------------------------
# Error path
# ---------------------------------------------------------------------------


def test_nonexistent_game_returns_404(client: TestClient):
    """Error path: non-existent game ID returns 404."""
    resp = client.get(
        f"/players/{DEFAULT_ID}/games/000000000000000000000000/spike",
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    )
    assert resp.status_code == 404
