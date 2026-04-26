"""Internal model for a structured round of Hundred and Ten"""

from dataclasses import dataclass

from hundredandten.engine import Player as EnginePlayer, Round as EngineRound

from .actions import Bid, Card, CardSuit, Play
from .trick import Trick


@dataclass
class DiscardRecord:
    """A record of a discard by a player"""

    discarded: list[Card]
    received: list[Card]


@dataclass
class Round:
    """
    Internal representation of a single round (completed or active).
    """

    _engine_round: EngineRound

    @property
    def dealer_player_id(self) -> str:
        return self._engine_round.dealer.identifier

    @property
    def initial_hands(self) -> dict[str, list[Card]]:
        # cheat and get initial hands by recreating the start of the round
        recreated_round = EngineRound(
            game_players=[
                EnginePlayer(p.identifier) for p in self._engine_round.players
            ],
            dealer_identifier=self._engine_round.dealer.identifier,
            seed=self._engine_round.seed,
        )
        return {
            p.identifier: [Card.from_engine(c) for c in p.hand]
            for p in recreated_round.players
        }

    @property
    def current_hands(self) -> dict[str, list[Card]]:
        return {
            p.identifier: [Card.from_engine(c) for c in p.hand]
            for p in self._engine_round.players
        }

    @property
    def discards(self) -> dict[str, DiscardRecord]:
        current_hands = self.current_hands
        initial_hands = self.initial_hands
        played_cards = {
            p.identifier: [
                Card.from_engine(play.card)
                for t in self._engine_round.tricks
                for play in t.plays
                if play.identifier == p.identifier
            ]
            for p in self._engine_round.players
        }
        return {
            d.identifier: DiscardRecord(
                discarded=[Card.from_engine(c) for c in d.cards],
                received=[
                    c
                    for c in (current_hands[d.identifier] + played_cards[d.identifier])
                    if c not in initial_hands[d.identifier]
                ],
            )
            for d in self._engine_round.discards
        }

    @property
    def bid_history(self) -> list[Bid]:
        return [Bid.from_engine(b) for b in self._engine_round.bids]

    @property
    def scores(self) -> dict[str, int]:
        round_scores = {}

        for score in self._engine_round.scores:
            round_scores[score.identifier] = (
                round_scores.get(score.identifier, 0) + score.value
            )

        return round_scores

    @property
    def trump(self) -> CardSuit | None:
        return (
            CardSuit[self._engine_round.trump.name]
            if self._engine_round.trump
            else None
        )

    @property
    def tricks(self) -> list[Trick]:
        return [
            Trick(
                bleeding=t.bleeding,
                plays=[Play.from_engine(p) for p in t.plays],
                winning_play=(
                    Play.from_engine(t.winning_play) if len(t.plays) else None
                ),
            )
            for t in self._engine_round.tricks
        ]

    @property
    def max_bid(self) -> Bid | None:
        """The greatest non-pass bid, or None if no bids have been placed or all passed"""
        if not self.bid_history:
            return None
        max_bid = max(reversed(self.bid_history), key=lambda b: b.amount)
        return max_bid if max_bid.amount > 0 else None
