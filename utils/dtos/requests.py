"""Pydantic models for API request bodies"""

from typing import Optional, Union

from pydantic import BaseModel

from utils.models import CardNumber, SelectableSuit, UnselectableSuit


class BidRequest(BaseModel):
    """Request body for bidding in a game"""

    amount: int


class CardRequest(BaseModel):
    """A card in a request"""

    suit: Union[SelectableSuit, UnselectableSuit]
    number: CardNumber


class DiscardRequest(BaseModel):
    """Request body for discarding cards"""

    cards: list[CardRequest]


class PlayRequest(BaseModel):
    """Request body for playing a card"""

    card: CardRequest


class SelectTrumpRequest(BaseModel):
    """Request body for selecting trump suit"""

    suit: SelectableSuit


class CreateLobbyRequest(BaseModel):
    """Request body for creating a lobby"""

    name: str
    accessibility: str = "PUBLIC"


class InviteRequest(BaseModel):
    """Request body for inviting players"""

    invitees: list[str] = []


class SearchLobbiesRequest(BaseModel):
    """Request body for searching lobbies"""

    searchText: str = ""
    max: int = 20


class SearchGamesRequest(BaseModel):
    """Request body for searching games"""

    searchText: str = ""
    max: int = 20
    statuses: Optional[list[str]] = None
    activePlayer: Optional[str] = None
    winner: Optional[str] = None


class UpdateUserRequest(BaseModel):
    """Request body for creating/updating a user"""

    name: str
    picture_url: Optional[str] = None
