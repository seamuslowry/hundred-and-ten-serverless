"""Format of a game of Hundred and Ten in the DB"""

from typing import Optional, TypedDict


class Person(TypedDict):
    """A class to model the DB format of a person"""

    identifier: str
    roles: list[str]
    automate: bool


class Card(TypedDict):
    """A class to model the DB format of a card"""

    suit: str
    number: str


class Move(TypedDict):
    """Base class for all game moves"""

    type: str
    identifier: str


class BidMove(Move):
    """A bid move"""

    amount: int


class SelectTrumpMove(Move):
    """A select trump move"""

    suit: str


class DiscardMove(Move):
    """A discard move"""

    cards: list[Card]


class PlayMove(Move):
    """A play card move"""

    card: Card


class UnpassMove(Move):
    """An unpass move"""

    pass


class Game(TypedDict):
    """A class to model the DB format of a Hundred and Ten game"""

    id: str
    name: str
    seed: str
    accessibility: str
    people: list[Person]
    moves: list[Move]
    started: bool


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
