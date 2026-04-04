"""Internal models for actions"""

from dataclasses import dataclass
from typing import Self, Union

from hundredandten.constants import (
    CardNumber as EngineCardNumber,
    CardSuit as EngineCardSuit,
)
from hundredandten.deck import Card as EngineCard
from hundredandten.trick import Play as EnginePlay

from .constants import BidAmount, CardNumber, CardSuit


@dataclass
class Card:
    """Internal representation of a card"""

    suit: CardSuit
    number: CardNumber

    @classmethod
    def from_engine(cls, engine_card: EngineCard) -> Self:
        return cls(
            suit=CardSuit[engine_card.suit.name],
            number=CardNumber(engine_card.number.name),
        )

    def to_engine(self) -> EngineCard:
        return EngineCard(
            suit=EngineCardSuit[self.suit.name],
            number=EngineCardNumber(self.number.name),
        )


@dataclass
class Play:
    """Internal representation of a play"""

    player_id: str
    card: Card

    @classmethod
    def from_engine(cls, engine_play: EnginePlay) -> Self:
        return cls(
            player_id=engine_play.identifier, card=Card.from_engine(engine_play.card)
        )

    def to_engine(self) -> EnginePlay:
        return EnginePlay(
            identifier=self.player_id, card=self.card.to_engine()
        )


@dataclass
class Bid:
    """A class to keep track of bid information"""

    player_id: str
    amount: BidAmount


@dataclass
class SelectTrump:
    """A class to represent the select trump action"""

    player_id: str
    suit: CardSuit


@dataclass
class Discard:
    """A class to keep track of one player's discard action"""

    player_id: str
    cards: list[Card]


type Action = Union[Bid, SelectTrump, Discard, Play]


@dataclass
class GameStart:
    """A class to represent the start of game event"""


@dataclass
class RoundStart:
    """A class to represent the start of round event"""

    dealer: str
    hands: dict[str, list[Card]]


@dataclass
class TrickStart:
    """A class to represent the start of trick event"""


@dataclass
class RoundEnd:
    """A class to represent the end of round event"""

    scores: dict[str, int]


@dataclass
class TrickEnd:
    """A class to represent the end of trick event"""

    winner: str


@dataclass
class GameEnd:
    """A class to represent the end of game event"""

    winner: str


type DerivedEvent = Union[
    GameStart, RoundStart, TrickStart, TrickEnd, RoundEnd, TrickEnd, GameEnd
]

type Event = Union[Action, DerivedEvent]
