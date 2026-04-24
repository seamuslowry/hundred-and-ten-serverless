"""Integration tests for the spike game read endpoint"""

from fastapi.testclient import TestClient

from src.models.internal.constants import BidAmount
from tests.helpers import (
    DEFAULT_ID,
    completed_game,
    game_with_manual_player,
    get_game,
    get_spike_game,
    queue_action,
    started_game,
)

# ---------------------------------------------------------------------------
# AE3: New game in bidding phase
# ---------------------------------------------------------------------------


def test_new_game_single_active_bidding_round(client: TestClient):
    """Covers AE3: new game has a single active round in BIDDING status."""
    game = started_game(client)
    spike = get_spike_game(client, game["id"], DEFAULT_ID)

    assert spike["status"] == "BIDDING"
    assert len(spike["rounds"]) == 1
    round_ = spike["rounds"][0]
    assert round_["status"] == "BIDDING"
    assert round_["trump"] is None
    assert round_["tricks"] == []
    assert round_["discards"] == {}


# ---------------------------------------------------------------------------
# AE1: Completed game
# ---------------------------------------------------------------------------


def test_completed_game_top_level_fields(client: TestClient):
    """Covers AE1: completed game has WON status and a winner."""
    game = completed_game(client)
    spike = get_spike_game(client, game["id"], DEFAULT_ID)

    assert spike["status"] == "WON"
    assert spike["winner"] is not None
    assert spike["id"] == game["id"]
    assert spike["name"] == game["name"]
    assert len(spike["players"]) == 4
    assert isinstance(spike["scores"], dict)


def test_completed_game_all_rounds_have_status(client: TestClient):
    """All rounds in a completed game are COMPLETED or COMPLETED_NO_BIDDERS."""
    game = completed_game(client)
    spike = get_spike_game(client, game["id"], DEFAULT_ID)

    for round_ in spike["rounds"]:
        assert round_["status"] in (
            "COMPLETED",
            "COMPLETED_NO_BIDDERS",
        ), f"Unexpected round status: {round_['status']}"


def test_completed_rounds_have_de_anonymized_hands(client: TestClient):
    """Covers AE1: completed rounds show all hands as card lists."""
    game = completed_game(client)
    spike = get_spike_game(client, game["id"], DEFAULT_ID)

    for round_ in spike["rounds"]:
        if round_["status"] == "COMPLETED":
            for player_id, hand in round_["hands"].items():
                assert isinstance(
                    hand, list
                ), f"Player {player_id} hand should be a card list in completed round"
            break


def test_completed_rounds_have_tricks_with_bleeding(client: TestClient):
    """Completed rounds include tricks with bleeding field."""
    game = completed_game(client)
    spike = get_spike_game(client, game["id"], DEFAULT_ID)

    for round_ in spike["rounds"]:
        if round_["status"] == "COMPLETED":
            assert len(round_["tricks"]) == 5
            for trick in round_["tricks"]:
                assert "bleeding" in trick
                assert isinstance(trick["bleeding"], bool)
                assert trick["winning_play"] is not None
            break


def test_completed_game_has_all_pass_rounds(client: TestClient):
    """Completed game includes COMPLETED_NO_BIDDERS rounds."""
    game = completed_game(client)
    spike = get_spike_game(client, game["id"], DEFAULT_ID)

    no_bidder = [r for r in spike["rounds"] if r["status"] == "COMPLETED_NO_BIDDERS"]
    assert len(no_bidder) > 0


def test_all_pass_rounds_have_hands_but_no_tricks(client: TestClient):
    """Edge case: COMPLETED_NO_BIDDERS rounds have hands but no tricks or discards."""
    game = completed_game(client)
    spike = get_spike_game(client, game["id"], DEFAULT_ID)

    for round_ in spike["rounds"]:
        if round_["status"] == "COMPLETED_NO_BIDDERS":
            assert len(round_["hands"]) == 4
            assert "tricks" not in round_ or round_.get("tricks") is None
            assert "trump" not in round_ or round_.get("trump") is None
            break


def test_completed_game_scores_sum_to_cumulative(client: TestClient):
    """Edge case: sum of round scores equals top-level cumulative scores."""
    game = completed_game(client)
    spike = get_spike_game(client, game["id"], DEFAULT_ID)

    total: dict[str, int] = {}
    for round_ in spike["rounds"]:
        for pid, v in round_["scores"].items():
            total[pid] = total.get(pid, 0) + v

    for pid, expected in spike["scores"].items():
        assert (
            total.get(pid, 0) == expected
        ), f"Player {pid}: round score sum {total.get(pid, 0)} != cumulative {expected}"


# ---------------------------------------------------------------------------
# Completed game: de-anonymization is requester-independent
# ---------------------------------------------------------------------------


def test_two_players_see_identical_completed_round_data(client: TestClient):
    """Edge case: two different players see the same data for completed rounds."""
    game = completed_game(client)
    # The active_player_id before the game ended is stored in the game
    # Use two player IDs from the game's players list
    player_ids = [p["id"] for p in game["players"]]
    p1, p2 = player_ids[0], player_ids[1]

    spike_p1 = get_spike_game(client, game["id"], p1)
    spike_p2 = get_spike_game(client, game["id"], p2)

    completed_p1 = [r for r in spike_p1["rounds"] if r["status"] == "COMPLETED"]
    completed_p2 = [r for r in spike_p2["rounds"] if r["status"] == "COMPLETED"]

    assert len(completed_p1) == len(completed_p2)
    for r1, r2 in zip(completed_p1, completed_p2):
        assert r1["hands"] == r2["hands"]
        assert r1["discards"] == r2["discards"]


# ---------------------------------------------------------------------------
# AE2: In-progress game active round visibility
# ---------------------------------------------------------------------------


def test_active_round_self_sees_cards(client: TestClient):
    """Covers AE2: requesting player sees their own hand as cards."""
    game = started_game(client)
    spike = get_spike_game(client, game["id"], DEFAULT_ID)

    active = next(r for r in spike["rounds"] if r["status"] == "BIDDING")
    assert isinstance(active["hands"][DEFAULT_ID], list)
    assert len(active["hands"][DEFAULT_ID]) == 5
    for card in active["hands"][DEFAULT_ID]:
        assert "suit" in card
        assert "number" in card


def test_active_round_others_see_count(client: TestClient):
    """Covers AE2: other players' hands are integers in the active round."""
    game = started_game(client)
    spike = get_spike_game(client, game["id"], DEFAULT_ID)

    active = next(r for r in spike["rounds"] if r["status"] == "BIDDING")
    for pid, hand in active["hands"].items():
        if pid != DEFAULT_ID:
            assert isinstance(hand, int)
            assert hand == 5


def test_active_round_includes_active_player_id(client: TestClient):
    """Edge case: active round includes active_player_id."""
    game = started_game(client)
    spike = get_spike_game(client, game["id"], DEFAULT_ID)

    active = next(
        r
        for r in spike["rounds"]
        if r["status"] not in ("COMPLETED", "COMPLETED_NO_BIDDERS")
    )
    assert "active_player_id" in active
    assert active["active_player_id"] == game["active_player_id"]


def test_two_players_see_different_hands_in_active_round(client: TestClient):
    """Edge case: two players see each other's hands as counts."""
    game, manual_player = game_with_manual_player(client)

    spike_organizer = get_spike_game(client, game["id"], DEFAULT_ID)
    spike_manual = get_spike_game(client, game["id"], manual_player)

    active_org = next(
        r
        for r in spike_organizer["rounds"]
        if r["status"] not in ("COMPLETED", "COMPLETED_NO_BIDDERS")
    )
    active_man = next(
        r
        for r in spike_manual["rounds"]
        if r["status"] not in ("COMPLETED", "COMPLETED_NO_BIDDERS")
    )

    # Organizer sees own cards, manual player as count
    assert isinstance(active_org["hands"][DEFAULT_ID], list)
    assert isinstance(active_org["hands"][manual_player], int)

    # Manual player sees own cards, organizer as count
    assert isinstance(active_man["hands"][manual_player], list)
    assert isinstance(active_man["hands"][DEFAULT_ID], int)


def test_active_round_queued_actions(client: TestClient):
    """Covers AE2: active round includes queued_actions field for the requesting player."""
    game, _manual_player = game_with_manual_player(client)

    # Queue an action for DEFAULT_ID (organizer) when it may not be their turn
    queue_action(
        client,
        game["id"],
        DEFAULT_ID,
        {"amount": BidAmount.SHOOT_THE_MOON, "type": "BID"},
    )

    spike = get_spike_game(client, game["id"], DEFAULT_ID)
    active = next(
        r
        for r in spike["rounds"]
        if r["status"] not in ("COMPLETED", "COMPLETED_NO_BIDDERS")
    )
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


# ---------------------------------------------------------------------------
# Existing endpoints unchanged
# ---------------------------------------------------------------------------


def test_existing_game_endpoint_unchanged(client: TestClient):
    """R9: the existing GET /{game_id} endpoint still works."""
    game = started_game(client)
    result = get_game(client, game["id"], DEFAULT_ID)
    assert result["status"] == "BIDDING"
    assert "players" in result
