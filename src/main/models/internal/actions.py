"""Internal models for actions"""

from dataclasses import dataclass
from typing import Self, Union

from hundredandten.actions import (
    Action as EngineAction,
)
from hundredandten.actions import (
    Bid as EngineBid,
)
from hundredandten.actions import (
    DetailedDiscard as EngineDetailedDiscard,
)
from hundredandten.actions import (
    Discard as EngineDiscard,
)
from hundredandten.actions import (
    Play as EnginePlay,
)
from hundredandten.actions import (
    SelectTrump as EngineSelectTrump,
)
from hundredandten.constants import (
    BidAmount as EngineBidAmount,
)
from hundredandten.constants import (
    CardNumber as EngineCardNumber,
)
from hundredandten.constants import (
    CardSuit as EngineCardSuit,
)
from hundredandten.constants import (
    SelectableSuit as EngineSelectableSuit,
)
from hundredandten.deck import Card as EngineCard

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
        return EnginePlay(identifier=self.player_id, card=self.card.to_engine())


@dataclass
class Bid:
    """A class to keep track of bid information"""

    player_id: str
    amount: BidAmount

    @classmethod
    def from_engine(cls, engine_bid: EngineBid) -> Self:
        return cls(
            player_id=engine_bid.identifier, amount=BidAmount(engine_bid.amount.value)
        )

    def to_engine(self) -> EngineBid:
        return EngineBid(
            identifier=self.player_id, amount=EngineBidAmount(self.amount.value)
        )


@dataclass
class SelectTrump:
    """A class to represent the select trump action"""

    player_id: str
    suit: CardSuit

    @classmethod
    def from_engine(cls, engine_select: EngineSelectTrump) -> Self:
        return cls(
            player_id=engine_select.identifier, suit=CardSuit[engine_select.suit.name]
        )

    def to_engine(self) -> EngineSelectTrump:
        return EngineSelectTrump(
            identifier=self.player_id, suit=EngineSelectableSuit[self.suit.name]
        )


@dataclass
class Discard:
    """A class to keep track of one player's discard action"""

    player_id: str
    cards: list[Card]

    @classmethod
    def from_engine(cls, engine_discard: EngineDiscard) -> Self:
        return cls(
            player_id=engine_discard.identifier,
            cards=[Card.from_engine(c) for c in engine_discard.cards],
        )

    def to_engine(self) -> EngineDiscard:
        return EngineDiscard(
            identifier=self.player_id, cards=[c.to_engine() for c in self.cards]
        )


type Action = Union[Bid, SelectTrump, Discard, Play]


class ActionFactory:
    @staticmethod
    def from_engine(a: EngineAction) -> Action:
        match (a):
            case EngineBid():
                return Bid.from_engine(a)
            case EngineSelectTrump():
                return SelectTrump.from_engine(a)
            case EngineDiscard() | EngineDetailedDiscard():
                return Discard.from_engine(a)
            case EnginePlay():
                return Play.from_engine(a)
        raise ValueError(
            f"Could not convert engine action {a} to an internal action"
        )  # pragma: nocover


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
