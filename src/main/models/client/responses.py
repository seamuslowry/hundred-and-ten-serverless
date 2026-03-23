"""Format of a game of Hundred and Ten on the client"""

from abc import ABC
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

from .constants import CardNumberName, SelectableSuit, Suit

# =============================================================================
# Actions & Events
# =============================================================================


class Sequential(ABC, BaseModel):
    """A class to indicate the subclass is sequential"""

    sequence: int


class Card(BaseModel):
    """A class to model the client format of a Hundred and Ten card"""

    suit: Suit
    number: CardNumberName


class BidAction(Sequential):
    """A class to model the client format of a Hundred and Ten bid action"""

    type: Literal["BID"]
    player_id: str
    amount: int


class SelectTrumpAction(Sequential):
    """A class to model the client format of a Hundred and Ten select trump action"""

    type: Literal["SELECT_TRUMP"]
    player_id: str
    suit: SelectableSuit


class DiscardAction(Sequential):
    """A class to model the client format of a Hundred and Ten discard action"""

    type: Literal["DISCARD"]
    player_id: str
    cards: Union[list[Card], int]


class PlayCardAction(Sequential):
    """A class to model the client format of a Hundred and Ten play action"""

    type: Literal["PLAY"]
    player_id: str
    card: Card


type GameAction = Union[BidAction, SelectTrumpAction, DiscardAction, PlayCardAction]


class GameStart(Sequential):
    """A class to model the client format of a Hundred and Ten game start event"""

    type: Literal["GAME_START"]


class RoundStart(Sequential):
    """A class to model the client format of a Hundred and Ten round start event"""

    type: Literal["ROUND_START"]
    dealer: str
    hands: dict[str, Union[list[Card], int]]


class TrickStart(Sequential):
    """A class to model the client format of a Hundred and Ten trick start event"""

    type: Literal["TRICK_START"]


class TrickEnd(Sequential):
    """A class to model the client format of a Hundred and Ten trick end event"""

    type: Literal["TRICK_END"]
    winner_player_id: str


class Score(BaseModel):
    """A class to model the client format of a score in a Hundred and Ten round end event"""

    player_id: str
    value: int


class RoundEnd(Sequential):
    """A class to model the client format of a Hundred and Ten round end event"""

    type: Literal["ROUND_END"]
    scores: list[Score]


class GameEnd(Sequential):
    """A class to model the client format of a Hundred and Ten game end event"""

    type: Literal["GAME_END"]
    winner_player_id: str


type GameEvent = Union[GameStart, RoundStart, TrickStart, TrickEnd, RoundEnd, GameEnd]

# Union type for all event types (used in results field for OpenAPI)
type Event = Annotated[
    Union[
        GameAction,
        GameEvent,
    ],
    Field(discriminator="type"),
]

# =============================================================================
# Unordered Actions
# =============================================================================


class UnorderedBid(BaseModel):
    """
    A class to model the client format of a Hundred and Ten bid action without context of sequence
    """

    type: Literal["BID"]
    player_id: str
    amount: int


class UnorderedSelectTrump(BaseModel):
    """
    A class to model the client format of a Hundred and Ten select trump action
    without context of sequence
    """

    type: Literal["SELECT_TRUMP"]
    player_id: str
    suit: SelectableSuit


class UnorderedDiscard(BaseModel):
    """
    A class to model the client format of a Hundred and Ten discard action
    without context of sequence
    """

    type: Literal["DISCARD"]
    player_id: str
    cards: Union[list[Card], int]


class UnorderedPlayCard(BaseModel):
    """
    A class to model the client format of a Hundred and Ten play action without context of sequence
    """

    type: Literal["PLAY"]
    player_id: str
    card: Card


# Union type for all unordered action types
# (used for suggestions, queued actions, and round internal actions)
type UnorderedActionResponse = Annotated[
    Union[UnorderedBid, UnorderedSelectTrump, UnorderedDiscard, UnorderedPlayCard],
    Field(discriminator="type"),
]


# =============================================================================
# Players
# =============================================================================


class Player(BaseModel):
    """A class to model the client format of a Hundred and Ten player"""

    id: str
    name: str
    picture_url: Optional[str] = None


class PlayerInGame(BaseModel):
    """A class to model the client format of a Hundred and Ten person"""

    id: str
    automate: bool
    queued_actions: list[UnorderedActionResponse]


class OtherPlayerInRound(BaseModel):
    """A class to model the client format of another Hundred and Ten player"""

    id: str
    hand_size: int


class SelfInRound(BaseModel):
    """A class to model the client format of the logged in Hundred and Ten player"""

    id: str
    hand: list[Card]


type PlayerInRound = Union[SelfInRound, OtherPlayerInRound]

# =============================================================================
# Games
# =============================================================================


class Trick(BaseModel):
    """A class to model the client format of a Hundred and Ten trick"""

    bleeding: bool
    plays: list[UnorderedPlayCard]
    winning_play: Optional[UnorderedPlayCard] = None


class Round(BaseModel):
    """A class to model the client format of a Hundred and Ten round"""

    players: list[PlayerInRound]
    dealer: PlayerInRound
    bidder: Optional[PlayerInRound] = None
    bid: Optional[int] = None
    trump: Optional[SelectableSuit] = None
    tricks: list[Trick]
    active_player: Optional[PlayerInRound] = None


class Game(BaseModel):
    """A class to model the client format of a Hundred and Ten game"""

    id: str
    name: str
    status: str


class WaitingGame(Game):
    """A class to model the client format of a waiting Hundred and Ten game"""

    accessibility: str
    organizer: PlayerInGame
    players: list[PlayerInGame]
    invitees: list[PlayerInGame]


class StartedGame(Game):
    """A class to model the client format of a started Hundred and Ten game"""

    round: Optional[Round] = None
    scores: dict[str, int]
    players: list[PlayerInGame]


class CompletedGame(Game):
    """A class to model the client format of a completed Hundred and Ten game"""

    winner: PlayerInGame
    organizer: PlayerInGame
    players: list[PlayerInGame]
    scores: dict[str, int]
