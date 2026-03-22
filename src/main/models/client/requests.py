"""Pydantic models for API request bodies"""

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

from .constants import CardNumberName, SelectableSuit, Suit


class BidRequest(BaseModel):
    """Request body for bidding in a game"""

    type: Literal["BID"]
    amount: int


class CardRequest(BaseModel):
    """A card in a request"""

    suit: Suit
    number: CardNumberName


class DiscardRequest(BaseModel):
    """Request body for discarding cards"""

    type: Literal["DISCARD"]
    cards: list[CardRequest]


class PlayRequest(BaseModel):
    """Request body for playing a card"""

    type: Literal["PLAY"]
    card: CardRequest


class SelectTrumpRequest(BaseModel):
    """Request body for selecting trump suit"""

    type: Literal["SELECT_TRUMP"]
    suit: SelectableSuit


type ActRequest = Annotated[
    Union[BidRequest, DiscardRequest, PlayRequest, SelectTrumpRequest],
    Field(discriminator="type"),
]


class CreateLobbyRequest(BaseModel):
    """Request body for creating a lobby"""

    name: str
    accessibility: str = "PUBLIC"


class InviteRequest(BaseModel):
    """Request body for inviting players"""

    invitees: list[str] = []


class SearchPlayersRequest(BaseModel):
    """Request body for searching players"""

    search_text: str = Field(default="", alias="searchText")
    offset: int = 0
    limit: int = 20


class SearchLobbiesRequest(BaseModel):
    """Request body for searching lobbies"""

    search_text: str = Field(default="", alias="searchText")
    offset: int = 0
    limit: int = 20


class SearchGamesRequest(BaseModel):
    """Request body for searching games"""

    search_text: str = Field(default="", alias="searchText")
    offset: int = 0
    limit: int = 20
    statuses: Optional[list[str]] = None
    active_player_id: Optional[str] = Field(default=None, alias="activePlayer")
    winner_player_id: Optional[str] = Field(default=None, alias="winner")


class LeaveGameRequest(BaseModel):
    """Request to leave a game as a player"""

    type: Literal["LEAVE"]


class KickGameRequest(BaseModel):
    """Request to kick a player from a game"""

    type: Literal["KICK"]
    player_id: str


type GamePlayerRequest = Annotated[
    Union[LeaveGameRequest, KickGameRequest], Field(discriminator="type")
]
