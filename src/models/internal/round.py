"""Internal model for a structured round of Hundred and Ten"""

from dataclasses import dataclass, field

from .actions import Bid, Card, CardSuit
from .trick import Trick


@dataclass
class Round:
    """Internal representation of a single round (completed or active).

    Instances are mutable by design: Game.rounds builds each Round
    incrementally during its action-walking replay before appending it
    to the completed list or returning it as the active round.
    """

    dealer: str
    hands: dict[str, list[Card]]
    bid_history: list[Bid] = field(default_factory=list)
    bidder: str | None = None
    bid_amount: int | None = None
    trump: CardSuit | None = None
    discards: dict[str, list[Card]] = field(default_factory=dict)
    tricks: list[Trick] = field(default_factory=list)
    scores: dict[str, int] | None = None
    completed: bool = False
