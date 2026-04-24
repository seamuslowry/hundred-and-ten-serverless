"""Internal model for a structured round of Hundred and Ten"""

from dataclasses import dataclass, field
from typing import Optional

from .actions import Bid, Card, CardSuit
from .trick import Trick


@dataclass
class Round:
    """Internal representation of a single round (completed or active)"""

    dealer: str
    hands: dict[str, list[Card]]
    bid_history: list[Bid] = field(default_factory=list)
    bidder: Optional[str] = None
    bid_amount: Optional[int] = None
    trump: Optional[CardSuit] = None
    discards: dict[str, list[Card]] = field(default_factory=dict)
    tricks: list[Trick] = field(default_factory=list)
    scores: Optional[dict[str, int]] = None
    completed: bool = False
