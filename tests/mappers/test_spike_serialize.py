"""Tests for the spike_game serializer"""

from src.mappers.client import serialize
from src.models.client import responses
from src.models.internal.game import Game
from src.models.internal.player import Human, NaiveCpu


def _make_completed_game(seed: str = "test-seed") -> Game:
    g = Game(
        organizer=Human("p1"),
        players=[NaiveCpu("p2"), NaiveCpu("p3"), NaiveCpu("p4")],
        seed=seed,
    )
    g.id = "test-id"
    g.leave("p1")
    return g


def _make_new_game(seed: str = "test-seed") -> Game:
    g = Game(
        organizer=Human("p1"),
        players=[NaiveCpu("p2"), NaiveCpu("p3"), NaiveCpu("p4")],
        seed=seed,
    )
    g.id = "test-id"
    return g


# ---------------------------------------------------------------------------
# Top-level SpikeGame structure
# ---------------------------------------------------------------------------


def test_spike_game_top_level_fields():
    """SpikeGame has id, name, status, players, scores, rounds."""
    g = _make_new_game()
    result = serialize.spike_game(g, "p1")
    assert result.id == "test-id"
    assert result.name == g.name
    assert result.status == "BIDDING"
    assert len(result.players) == 4
    assert isinstance(result.scores, dict)
    assert len(result.rounds) == 1


def test_spike_game_won_status_and_winner():
    """Completed game has status WON and a non-null winner."""
    g = _make_completed_game()
    result = serialize.spike_game(g, "p1")
    assert result.status == "WON"
    assert result.winner is not None
    assert result.winner.id == g.winner.id  # type: ignore[union-attr]


def test_spike_game_players_in_order():
    """Players are in game order (organizer first)."""
    g = _make_new_game()
    result = serialize.spike_game(g, "p1")
    expected_ids = [p.id for p in g.ordered_players]
    assert [p.id for p in result.players] == expected_ids


def test_spike_game_cumulative_scores():
    """Top-level scores match game.scores."""
    g = _make_completed_game()
    result = serialize.spike_game(g, "p1")
    assert result.scores == g.scores


# ---------------------------------------------------------------------------
# Round type discrimination
# ---------------------------------------------------------------------------


def test_completed_round_type():
    """Rounds with a bidder map to SpikeCompletedRound."""
    g = _make_completed_game()
    result = serialize.spike_game(g, "p1")
    completed = [r for r in result.rounds if r.status == "COMPLETED"]
    assert len(completed) > 0
    for r in completed:
        assert isinstance(r, responses.SpikeCompletedRound)


def test_all_pass_round_type():
    """All-pass rounds map to SpikeCompletedNoBiddersRound."""
    g = _make_completed_game()
    result = serialize.spike_game(g, "p1")
    no_bidder = [r for r in result.rounds if r.status == "COMPLETED_NO_BIDDERS"]
    assert len(no_bidder) > 0
    for r in no_bidder:
        assert isinstance(r, responses.SpikeCompletedNoBiddersRound)


def test_active_round_type():
    """Active round maps to SpikeActiveRound with correct phase status."""
    g = _make_new_game()
    result = serialize.spike_game(g, "p1")
    active = [r for r in result.rounds if isinstance(r, responses.SpikeActiveRound)]
    assert len(active) == 1
    assert active[0].status == "BIDDING"


# ---------------------------------------------------------------------------
# SpikeCompletedRound fields
# ---------------------------------------------------------------------------


def test_completed_round_all_fields_present():
    """Completed rounds have dealer, bidder, bid_amount, trump, bid_history, tricks, scores."""
    g = _make_completed_game()
    result = serialize.spike_game(g, "p1")
    for r in result.rounds:
        if r.status == "COMPLETED":
            assert r.dealer
            assert r.bidder
            assert r.bid_amount is not None
            assert r.trump is not None
            assert len(r.bid_history) > 0
            assert len(r.tricks) == 5
            assert isinstance(r.scores, dict)
            break


def test_completed_round_tricks_have_bleeding():
    """Tricks in completed rounds include bleeding."""
    g = _make_completed_game()
    result = serialize.spike_game(g, "p1")
    for r in result.rounds:
        if r.status == "COMPLETED":
            for trick in r.tricks:
                assert isinstance(trick.bleeding, bool)
                assert trick.winning_play is not None
            break


def test_completed_round_hands_de_anonymized():
    """Completed round hands are full card lists for all players."""
    g = _make_completed_game()
    result = serialize.spike_game(g, "p1")
    for r in result.rounds:
        if r.status == "COMPLETED":
            for pid, hand in r.hands.items():
                assert isinstance(hand, list), f"Player {pid} hand should be a list"
                assert len(hand) == 5
            break


def test_completed_round_de_anonymization_independent_of_requester():
    """Two different requesting players see identical completed round data."""
    g = _make_completed_game()
    result_p1 = serialize.spike_game(g, "p1")
    result_p2 = serialize.spike_game(g, "p2")

    completed_p1 = [r for r in result_p1.rounds if r.status == "COMPLETED"]
    completed_p2 = [r for r in result_p2.rounds if r.status == "COMPLETED"]

    assert len(completed_p1) == len(completed_p2)
    for r1, r2 in zip(completed_p1, completed_p2):
        assert r1.hands == r2.hands
        assert r1.discards == r2.discards


def test_completed_round_scores_sum_to_cumulative():
    """Sum of per-round scores equals top-level cumulative scores."""
    g = _make_completed_game()
    result = serialize.spike_game(g, "p1")
    total: dict[str, int] = {}
    for r in result.rounds:
        if r.status in ("COMPLETED", "COMPLETED_NO_BIDDERS"):
            for pid, v in r.scores.items():
                total[pid] = total.get(pid, 0) + v
    # Map to same key order as g.scores
    for pid, expected in g.scores.items():
        assert total.get(pid, 0) == expected, f"Player {pid} score mismatch"


# ---------------------------------------------------------------------------
# SpikeCompletedNoBiddersRound fields
# ---------------------------------------------------------------------------


def test_all_pass_round_has_hands():
    """All-pass rounds still include dealt hands."""
    g = _make_completed_game()
    result = serialize.spike_game(g, "p1")
    for r in result.rounds:
        if r.status == "COMPLETED_NO_BIDDERS":
            assert len(r.hands) == 4
            for hand in r.hands.values():
                assert isinstance(hand, list)
                assert len(hand) == 5
            break


# ---------------------------------------------------------------------------
# SpikeActiveRound visibility and fields
# ---------------------------------------------------------------------------


def test_active_round_self_sees_cards():
    """Requesting player sees their own hand as a list of cards."""
    g = _make_new_game()
    result = serialize.spike_game(g, "p1")
    active = next(r for r in result.rounds if isinstance(r, responses.SpikeActiveRound))
    assert isinstance(active.hands["p1"], list)
    assert len(active.hands["p1"]) == 5  # type: ignore[arg-type]


def test_active_round_others_see_count():
    """Other players' hands are integers in the active round."""
    g = _make_new_game()
    result = serialize.spike_game(g, "p1")
    active = next(r for r in result.rounds if isinstance(r, responses.SpikeActiveRound))
    for pid, hand in active.hands.items():
        if pid != "p1":
            assert isinstance(hand, int)
            assert hand == 5


def test_active_round_active_player_id():
    """Active round includes the correct active_player_id."""
    g = _make_new_game()
    result = serialize.spike_game(g, "p1")
    active = next(r for r in result.rounds if isinstance(r, responses.SpikeActiveRound))
    assert active.active_player_id == g.active_player_id


def test_active_round_queued_actions_for_self():
    """Requesting player's queued actions are included in the active round."""
    g = _make_new_game()
    result = serialize.spike_game(g, "p1")
    active = next(r for r in result.rounds if isinstance(r, responses.SpikeActiveRound))
    # queued_actions is a list (may be empty for a fresh game)
    assert isinstance(active.queued_actions, list)


def test_active_round_different_players_different_visibility():
    """Two players see each other's hands as counts in the active round."""
    from src.models.internal.player import Human

    g = Game(
        organizer=Human("p1"),
        players=[Human("p2"), NaiveCpu("p3"), NaiveCpu("p4")],
        seed="test-seed",
    )
    g.id = "test-id"

    result_p1 = serialize.spike_game(g, "p1")
    result_p2 = serialize.spike_game(g, "p2")

    active_p1 = next(
        r for r in result_p1.rounds if isinstance(r, responses.SpikeActiveRound)
    )
    active_p2 = next(
        r for r in result_p2.rounds if isinstance(r, responses.SpikeActiveRound)
    )

    # p1 sees own cards, sees p2 as count
    assert isinstance(active_p1.hands["p1"], list)
    assert isinstance(active_p1.hands["p2"], int)

    # p2 sees own cards, sees p1 as count
    assert isinstance(active_p2.hands["p2"], list)
    assert isinstance(active_p2.hands["p1"], int)
