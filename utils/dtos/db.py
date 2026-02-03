"""Format of a game of Hundred and Ten in the DB"""

from typing import Literal, Optional, TypedDict, Union


class Person(TypedDict):
    """A class to model the DB format of a person"""

    identifier: str
    roles: list[str]
    automate: bool


class Card(TypedDict):
    """A class to model the DB format of a card"""

    suit: str
    number: str


class BidMove(TypedDict):
    """A bid move"""

    type: Literal["bid"]
    identifier: str
    amount: int


class SelectTrumpMove(TypedDict):
    """A select trump move"""

    type: Literal["select_trump"]
    identifier: str
    suit: str


class DiscardMove(TypedDict):
    """A discard move"""

    type: Literal["discard"]
    identifier: str
    cards: list[Card]


class PlayMove(TypedDict):
    """A play card move"""

    type: Literal["play"]
    identifier: str
    card: Card


Move = Union[BidMove, SelectTrumpMove, DiscardMove, PlayMove]


class Game(TypedDict):
    """A class to model the DB format of a Hundred and Ten game"""

    id: str
    name: str
    seed: str
    accessibility: str
    people: list[Person]
    winner: Optional[str]
    active_player: Optional[str]
    moves: list[Move]
    lobby: bool
    status: str


class User(TypedDict):
    """A class to model the DB format of a Hundred and Ten user"""

    identifier: str
    name: str
    picture_url: Optional[str]


class SearchGame(TypedDict):
    """A class to model how the client will search for Hundred and Ten games"""

    name: str
    client: str
    statuses: Optional[list[str]]
    active_player: Optional[str]
    winner: Optional[str]
