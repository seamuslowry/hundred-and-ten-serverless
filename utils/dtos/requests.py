"""Pydantic models for API request bodies"""

from typing import Optional

from pydantic import BaseModel


class BidRequest(BaseModel):
    """Request body for bidding in a game"""

    amount: int


class CardRequest(BaseModel):
    """A card in a request"""

    suit: str
    number: str


class DiscardRequest(BaseModel):
    """Request body for discarding cards"""

    cards: list[CardRequest]


class PlayRequest(BaseModel):
    """Request body for playing a card"""

    card: CardRequest


class SelectTrumpRequest(BaseModel):
    """Request body for selecting trump suit"""

    suit: str


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
