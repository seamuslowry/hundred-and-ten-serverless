"""Internal model for a structured round of Hundred and Ten"""

from dataclasses import dataclass, field

from .actions import Bid, Card, CardSuit
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

    dealer_player_id: str
    hands: dict[str, list[Card]]
    scores: dict[str, int]
    bid_history: list[Bid] = field(default_factory=list)
    trump: CardSuit | None = None
    discards: dict[str, DiscardRecord] = field(default_factory=dict)
    tricks: list[Trick] = field(default_factory=list)

    @property
    def max_bid(self) -> Bid | None:
        """The greatest non-pass bid, or None if no bids have been placed or all passed"""
        if not self.bid_history:
            return None
        max_bid = max(reversed(self.bid_history), key=lambda b: b.amount)
        return max_bid if max_bid.amount > 0 else None
