"""Internal models for actions"""

from dataclasses import dataclass
from typing import Self

from hundredandten.engine import (
    Action as EngineAction,
    Bid as EngineBid,
    BidAmount as EngineBidAmount,
    Card as EngineCard,
    CardNumber as EngineCardNumber,
    CardSuit as EngineCardSuit,
    Discard as EngineDiscard,
    Play as EnginePlay,
    SelectableSuit as EngineSelectableSuit,
    SelectTrump as EngineSelectTrump,
)

from .constants import BidAmount, CardNumber, CardSuit


@dataclass(frozen=True)
class Card:
    """Internal representation of a card"""

    suit: CardSuit
    number: CardNumber

    @classmethod
    def from_engine(cls, engine_card: EngineCard) -> Self:
        """Create an internal Card from an engine Card."""
        return cls(
            suit=CardSuit[engine_card.suit.name],
            number=CardNumber(engine_card.number.name),
        )

    def to_engine(self) -> EngineCard:
        """Convert this internal Card to an engine Card."""
        return EngineCard(
            suit=EngineCardSuit[self.suit.name],
            number=EngineCardNumber(self.number.name),
        )


@dataclass(frozen=True)
class Play:
    """Internal representation of a play"""

    player_id: str
    card: Card

    @classmethod
    def from_engine(cls, engine_play: EnginePlay) -> Self:
        """Create an internal Play from an engine Play."""
        return cls(
            player_id=engine_play.identifier, card=Card.from_engine(engine_play.card)
        )

    def to_engine(self) -> EnginePlay:
        """Convert this internal Play to an engine Play."""
        return EnginePlay(identifier=self.player_id, card=self.card.to_engine())


@dataclass(frozen=True)
class Bid:
    """A class to keep track of bid information"""

    player_id: str
    amount: BidAmount

    @classmethod
    def from_engine(cls, engine_bid: EngineBid) -> Self:
        """Create an internal Bid from an engine Bid."""
        return cls(
            player_id=engine_bid.identifier, amount=BidAmount(engine_bid.amount.value)
        )

    def to_engine(self) -> EngineBid:
        """Convert this internal Bid to an engine Bid."""
        return EngineBid(
            identifier=self.player_id, amount=EngineBidAmount(self.amount.value)
        )


@dataclass(frozen=True)
class SelectTrump:
    """A class to represent the select trump action"""

    player_id: str
    suit: CardSuit

    @classmethod
    def from_engine(cls, engine_select: EngineSelectTrump) -> Self:
        """Create an internal SelectTrump from an engine SelectTrump."""
        return cls(
            player_id=engine_select.identifier, suit=CardSuit[engine_select.suit.name]
        )

    def to_engine(self) -> EngineSelectTrump:
        """Convert this internal SelectTrump to an engine SelectTrump."""
        return EngineSelectTrump(
            identifier=self.player_id, suit=EngineSelectableSuit[self.suit.name]
        )


@dataclass(frozen=True)
class Discard:
    """A class to keep track of one player's discard action"""

    player_id: str
    cards: tuple[Card, ...]

    @classmethod
    def from_engine(cls, engine_discard: EngineDiscard) -> Self:
        """Create an internal Discard from an engine Discard."""
        return cls(
            player_id=engine_discard.identifier,
            cards=tuple(Card.from_engine(c) for c in engine_discard.cards),
        )

    def to_engine(self) -> EngineDiscard:
        """Convert this internal Discard to an engine Discard."""
        return EngineDiscard(
            identifier=self.player_id, cards=[c.to_engine() for c in self.cards]
        )


type Action = Bid | SelectTrump | Discard | Play


class ActionFactory:
    """Factory class for creating internal actions from engine actions."""

    @staticmethod
    def from_engine(a: EngineAction) -> Action:
        """Create an internal Action from an engine Action."""
        match a:
            case EngineBid():
                return Bid.from_engine(a)
            case EngineSelectTrump():
                return SelectTrump.from_engine(a)
            case EngineDiscard():
                return Discard.from_engine(a)
            case EnginePlay():
                return Play.from_engine(a)
        raise ValueError(
            f"Could not convert engine action {a} to an internal action"
        )  # pragma: nocover


@dataclass(frozen=True)
class GameStart:
    """A class to represent the start of game event"""


@dataclass(frozen=True)
class RoundStart:
    """A class to represent the start of round event"""

    dealer: str
    hands: dict[str, list[Card]]


@dataclass(frozen=True)
class TrickStart:
    """A class to represent the start of trick event"""


@dataclass(frozen=True)
class RoundEnd:
    """A class to represent the end of round event"""

    scores: dict[str, int]


@dataclass(frozen=True)
class TrickEnd:
    """A class to represent the end of trick event"""

    winner: str


@dataclass(frozen=True)
class GameEnd:
    """A class to represent the end of game event"""

    winner: str


type DerivedEvent = GameStart | RoundStart | TrickStart | TrickEnd | RoundEnd | GameEnd

type Event = Action | DerivedEvent
