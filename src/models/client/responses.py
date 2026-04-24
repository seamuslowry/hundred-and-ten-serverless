"""Format of a game of Hundred and Ten on the client"""

from abc import ABC
from enum import Enum
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


type GameAction = BidAction | SelectTrumpAction | DiscardAction | PlayCardAction


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


type GameEvent = GameStart | RoundStart | TrickStart | TrickEnd | RoundEnd | GameEnd

# Union type for all event types (used in results field for OpenAPI)
type Event = Annotated[
    Union[
        GameAction,
        GameEvent,
    ],
    Field(discriminator="type"),
]

# =============================================================================
#  Queued Actions
# =============================================================================


class QueuedBid(BaseModel):
    """
    A class to model the client format of a Hundred and Ten bid action without context of sequence
    """

    type: Literal["BID"]
    player_id: str
    amount: int


class QueuedSelectTrump(BaseModel):
    """
    A class to model the client format of a Hundred and Ten select trump action
    without context of sequence
    """

    type: Literal["SELECT_TRUMP"]
    player_id: str
    suit: SelectableSuit


class QueuedDiscard(BaseModel):
    """
    A class to model the client format of a Hundred and Ten discard action
    without context of sequence
    """

    type: Literal["DISCARD"]
    player_id: str
    cards: Union[list[Card], int]


class QueuedPlayCard(BaseModel):
    """
    A class to model the client format of a Hundred and Ten play action without context of sequence
    """

    type: Literal["PLAY"]
    player_id: str
    card: Card


# Union type for all unordered action types
# (used for suggestions and queued actions)
type UnorderedActionResponse = Annotated[
    Union[QueuedBid, QueuedSelectTrump, QueuedDiscard, QueuedPlayCard],
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


class PlayerType(Enum):
    """The type of players that may be in a game"""

    HUMAN = "human"
    CPU_EASY = "cpu-easy"


class PlayerInGame(BaseModel):
    """A class to model the client format of a Hundred and Ten person"""

    id: str
    type: PlayerType


class OtherPlayerInRound(BaseModel):
    """A class to model the client format of another Hundred and Ten player"""

    id: str
    hand_size: int
    type: PlayerType


class SelfInRound(BaseModel):
    """A class to model the client format of the logged in Hundred and Ten player"""

    id: str
    type: PlayerType
    hand: list[Card]
    queued_actions: list[UnorderedActionResponse]


type PlayerInRound = SelfInRound | OtherPlayerInRound

# =============================================================================
# Games
# =============================================================================


class Trick(BaseModel):
    """A class to model the client format of a Hundred and Ten trick"""

    bleeding: bool
    plays: list[QueuedPlayCard]
    winning_play: Optional[QueuedPlayCard] = None


class Game(BaseModel):
    """A class to model the client format of a Hundred and Ten game"""

    id: str
    name: str


class WaitingGame(Game):
    """A class to model the client format of a waiting Hundred and Ten game"""

    accessibility: str
    organizer: PlayerInGame
    players: list[PlayerInGame]
    invitees: list[PlayerInGame]


class StartedGame(Game):
    """A class to model the client format of a started Hundred and Ten game"""

    status: str
    scores: dict[str, int]
    dealer_player_id: str
    bidder_player_id: Optional[str]
    active_player_id: Optional[str]
    bid_amount: Optional[int]
    trump: Optional[SelectableSuit]
    tricks: list[Trick]
    players: list[PlayerInRound]


class CompletedGame(Game):
    """A class to model the client format of a completed Hundred and Ten game"""

    status: str
    winner: PlayerInGame
    organizer: PlayerInGame
    players: list[PlayerInGame]
    scores: dict[str, int]


# =============================================================================
# Spike game response models (round-based, unified in-progress/completed view)
# =============================================================================


class SpikeBid(BaseModel):
    """A single bid in a round's bid history"""

    player_id: str
    amount: int


class SpikeTrick(BaseModel):
    """A trick within a spike round"""

    bleeding: bool
    plays: list[QueuedPlayCard]
    winning_play: Optional[QueuedPlayCard] = None


class SpikeCompletedRound(BaseModel):
    """A completed round where bidding was won and tricks were played"""

    status: Literal["COMPLETED"]
    dealer_player_id: str
    bidder_player_id: str
    bid_amount: int
    trump: SelectableSuit
    bid_history: list[SpikeBid]
    hands: dict[str, list[Card]]
    discards: dict[str, list[Card]]
    tricks: list[SpikeTrick]
    scores: dict[str, int]


class SpikeCompletedNoBiddersRound(BaseModel):
    """A completed round where all players passed (no bidder, no tricks)"""

    status: Literal["COMPLETED_NO_BIDDERS"]
    dealer_player_id: str
    initial_hands: dict[str, list[Card]]


class SpikeActiveRound(BaseModel):
    """The current active round (bidding, trump selection, discarding, or tricks)"""

    status: Literal["BIDDING", "TRUMP_SELECTION", "DISCARD", "TRICKS"]
    dealer_player_id: str
    bid_history: list[SpikeBid]
    hands: dict[str, Union[list[Card], int]]
    discards: dict[str, Union[list[Card], int]]
    bidder_player_id: Optional[str] = None
    bid_amount: Optional[int] = None
    trump: Optional[SelectableSuit] = None
    tricks: list[SpikeTrick]
    active_player_id: str
    queued_actions: list[UnorderedActionResponse]


type SpikeRound = Annotated[
    Union[SpikeCompletedRound, SpikeCompletedNoBiddersRound, SpikeActiveRound],
    Field(discriminator="status"),
]


class SpikeGame(BaseModel):
    """Unified round-based game response for the spike endpoint"""

    id: str
    name: str
    status: str
    winner: Optional[PlayerInGame] = None
    players: list[PlayerInGame]
    scores: dict[str, int]
    rounds: list[SpikeRound]
