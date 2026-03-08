"""Pydantic models for database documents in Hundred and Ten"""

from typing import Annotated, Any, Literal, Optional, Union

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def _parse_objectid(v: Any) -> Optional[str]:
    """Convert BSON ObjectId to string, or pass through string/None values."""
    if v is None:
        return None
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str):
        return v
    raise ValueError(f"Cannot parse ObjectId from {type(v)}")


OptionalObjectId = Annotated[Optional[str], BeforeValidator(_parse_objectid)]


class Person(BaseModel):
    """A class to model the DB format of a person"""

    identifier: str
    automate: bool


class Card(BaseModel):
    """A class to model the DB format of a card"""

    suit: str
    number: str


class BidMove(BaseModel):
    """A bid move"""

    type: Literal["bid"] = "bid"
    identifier: str
    amount: int


class SelectTrumpMove(BaseModel):
    """A select trump move"""

    type: Literal["select_trump"] = "select_trump"
    identifier: str
    suit: str


class DiscardMove(BaseModel):
    """A discard move"""

    type: Literal["discard"] = "discard"
    identifier: str
    cards: list[Card]


class PlayMove(BaseModel):
    """A play card move"""

    type: Literal["play"] = "play"
    identifier: str
    card: Card


Move = Annotated[
    Union[BidMove, SelectTrumpMove, DiscardMove, PlayMove],
    Field(discriminator="type"),
]


class Lobby(BaseModel):
    """A class to model the DB format of a Hundred and Ten lobby"""

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["lobby"] = "lobby"
    id: OptionalObjectId = Field(None, alias="_id")
    name: str
    seed: str
    accessibility: str
    organizer: Person
    players: list[Person]
    invitees: list[Person]


class Game(BaseModel):
    """A class to model the DB format of a Hundred and Ten game"""

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["game"] = "game"
    id: OptionalObjectId = Field(None, alias="_id")
    name: str
    seed: str
    accessibility: str
    organizer: Person
    players: list[Person]
    winner: Optional[str] = None
    active_player: Optional[str] = None
    moves: list[Move]
    status: str


class User(BaseModel):
    """A class to model the DB format of a Hundred and Ten user"""

    identifier: str
    name: str
    picture_url: Optional[str] = None


class SearchLobby(BaseModel):
    """A class to model how the client will search for lobbies"""

    name: str
    client: str


class SearchGame(BaseModel):
    """A class to model how the client will search for games"""

    name: str
    client: str
    statuses: Optional[list[str]] = None
    active_player: Optional[str] = None
    winner: Optional[str] = None
