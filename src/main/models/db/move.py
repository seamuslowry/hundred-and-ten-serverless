"""Format of a moves of Hundred and Ten in the DB"""

from abc import ABC
from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class Suit(str, Enum):
    """All card suits (selectable + unselectable) as string names for DB"""

    JOKER = "JOKER"
    DIAMONDS = "DIAMONDS"
    CLUBS = "CLUBS"
    HEARTS = "HEARTS"
    SPADES = "SPADES"


class SelectableSuit(str, Enum):
    """Selectable trump suits as string names for DB"""

    DIAMONDS = "DIAMONDS"
    SPADES = "SPADES"
    CLUBS = "CLUBS"
    HEARTS = "HEARTS"


class CardNumber(str, Enum):
    """Card number names for DB"""

    JOKER = "JOKER"
    ACE = "ACE"
    KING = "KING"
    QUEEN = "QUEEN"
    JACK = "JACK"
    TEN = "TEN"
    NINE = "NINE"
    EIGHT = "EIGHT"
    SEVEN = "SEVEN"
    SIX = "SIX"
    FIVE = "FIVE"
    FOUR = "FOUR"
    THREE = "THREE"
    TWO = "TWO"


class Card(BaseModel):
    """A class to model the DB format of a card"""

    suit: Suit
    number: CardNumber


class AbstractMove(ABC, BaseModel):
    """A base class for move records"""


class BidMove(AbstractMove):
    """A bid move"""

    type: Literal["bid"] = "bid"
    identifier: str
    amount: int


class SelectTrumpMove(AbstractMove):
    """A select trump move"""

    type: Literal["select_trump"] = "select_trump"
    identifier: str
    suit: SelectableSuit


class DiscardMove(AbstractMove):
    """A discard move"""

    type: Literal["discard"] = "discard"
    identifier: str
    cards: list[Card]


class PlayMove(AbstractMove):
    """A play card move"""

    type: Literal["play"] = "play"
    identifier: str
    card: Card


type Move = Annotated[
    Union[BidMove, SelectTrumpMove, DiscardMove, PlayMove], Field(discriminator="type")
]
