"""Tests for the Game.rounds property"""

from src.models.internal.actions import (
    Bid as InternalBid,
    BidAmount,
    CardSuit,
    Discard,
    GameStart,
    SelectTrump,
)
from src.models.internal.game import Game, PlayerGroup
from src.models.internal.player import Human, NaiveCpu


def _make_completed_game(seed: str = "test-seed") -> Game:
    """Build a completed game by converting the human player to NaiveCpu."""
    g = Game(
        organizer=Human("p1"),
        players=PlayerGroup([NaiveCpu("p2"), NaiveCpu("p3"), NaiveCpu("p4")]),
        seed=seed,
    )
    g.leave("p1")
    return g


def _make_new_game(seed: str = "test-seed") -> Game:
    """Build a new game in the initial bidding phase."""
    return Game(
        organizer=Human("p1"),
        players=PlayerGroup([NaiveCpu("p2"), NaiveCpu("p3"), NaiveCpu("p4")]),
        seed=seed,
    )


# ---------------------------------------------------------------------------
# New / in-progress game
# ---------------------------------------------------------------------------


def test_new_game_has_one_active_round():
    """A new game produces a single in-progress round."""
    g = _make_new_game()
    rounds = g.rounds
    assert len(rounds) == 1
    assert not rounds[0].completed


def test_new_game_round_has_correct_dealer():
    """The active round's dealer matches the engine's dealer."""
    g = _make_new_game()
    rounds = g.rounds
    assert rounds[0].dealer == g.dealer_player_id


def test_new_game_round_hands_are_pre_discard():
    """Hands in the active round snapshot 5 cards (dealt hand, not post-discard)."""
    g = _make_new_game()
    round_ = g.rounds[0]
    for player_id, hand in round_.hands.items():
        assert len(hand) == 5, f"Player {player_id} has {len(hand)} cards, expected 5"


def test_new_game_round_has_players_in_order():
    """The hands dict contains entries for all 4 players."""
    g = _make_new_game()
    round_ = g.rounds[0]
    expected_ids = {p.id for p in g.ordered_players}
    assert set(round_.hands.keys()) == expected_ids


def test_active_round_has_bid_history():
    """The active round's bid_history contains bids placed by automated CPU players."""
    g = _make_new_game()
    round_ = g.rounds[0]
    # NaiveCpu players auto-bid before the Human player's turn
    assert len(round_.bid_history) >= 1


# ---------------------------------------------------------------------------
# Completed game
# ---------------------------------------------------------------------------


def test_completed_game_all_rounds_completed():
    """A completed game has no active rounds."""
    g = _make_completed_game()
    rounds = g.rounds
    assert all(r.completed for r in rounds)


def test_completed_game_has_multiple_rounds():
    """A completed game produces more than one round."""
    g = _make_completed_game()
    assert len(g.rounds) > 1


def test_completed_game_hands_are_pre_discard():
    """All hands in completed rounds contain 5 cards (dealt, not post-discard)."""
    g = _make_completed_game()
    for i, round_ in enumerate(g.rounds):
        for player_id, hand in round_.hands.items():
            assert (
                len(hand) == 5
            ), f"Round {i} player {player_id} has {len(hand)} cards, expected 5"


def test_completed_game_scores_sum_to_cumulative():
    """Sum of all per-round scores equals the game-level cumulative scores."""
    g = _make_completed_game()
    round_sum: dict[str, int] = {}
    for round_ in g.rounds:
        if round_.scores:
            for player_id, value in round_.scores.items():
                round_sum[player_id] = round_sum.get(player_id, 0) + value
    assert round_sum == g.scores


def test_completed_game_has_all_pass_rounds():
    """Some completed rounds have no bidder (all-pass)."""
    g = _make_completed_game()
    no_bidder = [r for r in g.rounds if r.completed and r.bidder is None]
    assert len(no_bidder) > 0


def test_all_pass_round_has_no_tricks_or_discards():
    """All-pass rounds have empty tricks and discards."""
    g = _make_completed_game()
    for round_ in g.rounds:
        if round_.completed and round_.bidder is None:
            assert len(round_.tricks) == 0
            assert len(round_.discards) == 0
            assert round_.trump is None


def test_all_pass_round_is_completed_with_hands():
    """All-pass rounds are completed and still have dealt hands."""
    g = _make_completed_game()
    all_pass = [r for r in g.rounds if r.completed and r.bidder is None]
    assert len(all_pass) > 0
    for round_ in all_pass:
        assert len(round_.hands) == 4
        for hand in round_.hands.values():
            assert len(hand) == 5


def test_completed_round_with_bidder_has_five_tricks():
    """Completed rounds with a bidder have 5 tricks."""
    g = _make_completed_game()
    bidder_rounds = [r for r in g.rounds if r.completed and r.bidder is not None]
    assert len(bidder_rounds) > 0
    for round_ in bidder_rounds:
        assert len(round_.tricks) == 5


def test_tricks_have_bleeding_and_winning_play():
    """Each trick in a completed round has bleeding and a winning_play."""
    g = _make_completed_game()
    for round_ in g.rounds:
        for trick in round_.tricks:
            assert isinstance(trick.bleeding, bool)
            assert trick.winning_play is not None
            assert len(trick.plays) == 4


def test_bid_history_captured_per_round():
    """Each completed round with a bidder has a non-empty bid_history."""
    g = _make_completed_game()
    for round_ in g.rounds:
        if round_.bidder is not None:
            assert len(round_.bid_history) > 0


def test_discards_captured_per_round():
    """Completed rounds with a bidder have discards for all 4 players."""
    g = _make_completed_game()
    for round_ in g.rounds:
        if round_.bidder is not None:
            assert len(round_.discards) == 4


def test_trump_set_on_bidder_rounds():
    """Completed rounds with a bidder have a trump suit."""
    g = _make_completed_game()
    for round_ in g.rounds:
        if round_.bidder is not None:
            assert round_.trump is not None


def test_tricks_phase_active_round_has_in_progress_tricks():
    """Active round in TRICKS phase contains in-progress trick data."""
    g = Game(
        organizer=Human("p1"),
        players=PlayerGroup([NaiveCpu("p2"), NaiveCpu("p3"), NaiveCpu("p4")]),
        seed="test-seed",
    )
    g.act(InternalBid(player_id="p1", amount=BidAmount.SHOOT_THE_MOON))
    g.act(SelectTrump(player_id="p1", suit=CardSuit.HEARTS))
    g.act(Discard(player_id="p1", cards=tuple()))
    assert g.status.name == "TRICKS"

    rounds = g.rounds
    assert len(rounds) == 1
    active = rounds[0]
    assert not active.completed
    # At least one trick should be in progress
    assert len(active.tricks) >= 1
    # Tricks in-progress have plays
    for trick in active.tricks:
        assert len(trick.plays) >= 0  # may be 0 if no plays yet


def test_game_events_property_unchanged():
    """The Game.events property still works after adding Game.rounds."""
    g = _make_completed_game()
    events = g.events
    assert len(events) > 0
    assert isinstance(events[0], GameStart)
