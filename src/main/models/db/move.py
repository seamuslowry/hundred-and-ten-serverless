"""Format of a moves of Hundred and Ten in the DB"""


from abc import ABC
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class Card(BaseModel):
    """A class to model the DB format of a card"""

    suit: str
    number: str


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
    suit: str


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
