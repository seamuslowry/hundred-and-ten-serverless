"""Pydantic models for API request bodies"""

from typing import Annotated, Literal, Optional, Union

from pydantic import Field

from .constants import CardNumberName, SelectableSuit, Suit
from .shared import ClientModel


class BidRequest(ClientModel):
    """Request body for bidding in a game"""

    type: Literal["BID"]
    amount: int


class CardRequest(ClientModel):
    """A card in a request"""

    suit: Suit
    number: CardNumberName


class DiscardRequest(ClientModel):
    """Request body for discarding cards"""

    type: Literal["DISCARD"]
    cards: list[CardRequest]


class PlayRequest(ClientModel):
    """Request body for playing a card"""

    type: Literal["PLAY"]
    card: CardRequest


class SelectTrumpRequest(ClientModel):
    """Request body for selecting trump suit"""

    type: Literal["SELECT_TRUMP"]
    suit: SelectableSuit


type ActRequest = Annotated[
    Union[BidRequest, DiscardRequest, PlayRequest, SelectTrumpRequest],
    Field(discriminator="type"),
]


class CreateLobbyRequest(ClientModel):
    """Request body for creating a lobby"""

    name: str
    accessibility: str = "PUBLIC"


class SearchPlayersRequest(ClientModel):
    """Request body for searching players"""

    search_text: str = ""
    offset: int = 0
    limit: int = 20


class SearchLobbiesRequest(ClientModel):
    """Request body for searching lobbies"""

    search_text: str = ""
    offset: int = 0
    limit: int = 20


class SearchGamesRequest(ClientModel):
    """Request body for searching games"""

    search_text: str = ""
    offset: int = 0
    limit: int = 20
    statuses: Optional[list[str]] = None
    # Non-standard aliases kept intentionally: API contract uses "activePlayer"/"winner"
    active_player_id: Optional[str] = Field(default=None, alias="activePlayer")
    winner_player_id: Optional[str] = Field(default=None, alias="winner")


class GamePlayerLeaveRequest(ClientModel):
    """Request to leave a game as a player"""

    type: Literal["LEAVE"]


class GamePlayerKickRequest(ClientModel):
    """Request to kick a player from a game"""

    type: Literal["KICK"]
    player_id: str


type GamePlayerRequest = Annotated[
    Union[GamePlayerLeaveRequest, GamePlayerKickRequest], Field(discriminator="type")
]


class LobbyPlayerLeaveRequest(ClientModel):
    """Request to leave a lobby as a player"""

    type: Literal["LEAVE"]


class LobbyPlayerJoinRequest(ClientModel):
    """Request to join a lobby as a player"""

    type: Literal["JOIN"]


class LobbyPlayerInviteRequest(ClientModel):
    """Request to invite another player to a lobby"""

    type: Literal["INVITE"]
    player_id: str


class LobbyPlayerKickRequest(ClientModel):
    """Request to kick a player from a lobby"""

    type: Literal["KICK"]
    player_id: str


type LobbyPlayerRequest = Annotated[
    Union[
        LobbyPlayerLeaveRequest,
        LobbyPlayerJoinRequest,
        LobbyPlayerInviteRequest,
        LobbyPlayerKickRequest,
    ],
    Field(discriminator="type"),
]
