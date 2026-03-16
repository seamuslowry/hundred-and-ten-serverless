"""Format of a game of Hundred and Ten on the client"""

from typing import Literal, Optional, Union

from pydantic import BaseModel

from .constants import CardNumberName, SelectableSuit, Suit


class Player(BaseModel):
    """A class to model the client format of a Hundred and Ten player"""

    id: str
    name: str
    picture_url: Optional[str] = None


class PlayerInGame(BaseModel):
    """A class to model the client format of a Hundred and Ten person"""

    id: str
    automate: bool


class OtherPlayerInRound(BaseModel):
    """A class to model the client format of another Hundred and Ten player"""

    id: str
    hand_size: int


class Card(BaseModel):
    """A class to model the client format of a Hundred and Ten card"""

    suit: Suit
    number: CardNumberName


class SelfInRound(BaseModel):
    """A class to model the client format of the logged in Hundred and Ten player"""

    id: str
    hand: list[Card]
    prepassed: bool


type PlayerInRound = Union[SelfInRound, OtherPlayerInRound]

# =============================================================================
# Event types
# =============================================================================


class Event(BaseModel):
    """A class to model the client format of a Hundred and Ten event"""


class GameStart(Event):
    """A class to model the client format of a Hundred and Ten game start event"""

    type: Literal["GAME_START"] = "GAME_START"


class RoundStart(Event):
    """A class to model the client format of a Hundred and Ten round start event"""

    type: Literal["ROUND_START"] = "ROUND_START"
    dealer: str
    hands: dict[str, Union[list[Card], int]]


class Bid(Event):
    """A class to model the client format of a Hundred and Ten bid event"""

    type: Literal["BID"] = "BID"
    player_id: str
    amount: int


class SelectTrump(Event):
    """A class to model the client format of a Hundred and Ten select trump event"""

    type: Literal["SELECT_TRUMP"] = "SELECT_TRUMP"
    player_id: str
    suit: SelectableSuit


class Discard(Event):
    """A class to model the client format of a Hundred and Ten discard event"""

    type: Literal["DISCARD"] = "DISCARD"
    player_id: str
    discards: Union[list[Card], int]


class TrickStart(Event):
    """A class to model the client format of a Hundred and Ten trick start event"""

    type: Literal["TRICK_START"] = "TRICK_START"


class PlayEvent(Event):
    """A class to model the client format of a Hundred and Ten play event"""

    type: Literal["PLAY"] = "PLAY"
    player_id: str
    card: Card


class TrickEnd(Event):
    """A class to model the client format of a Hundred and Ten trick end event"""

    type: Literal["TRICK_END"] = "TRICK_END"
    winner_player_id: str


class Score(BaseModel):
    """A class to model the client format of a score in a Hundred and Ten round end event"""

    player_id: str
    value: int


class RoundEnd(Event):
    """A class to model the client format of a Hundred and Ten round end event"""

    type: Literal["ROUND_END"] = "ROUND_END"
    scores: list[Score]


class GameEnd(Event):
    """A class to model the client format of a Hundred and Ten game end event"""

    type: Literal["GAME_END"] = "GAME_END"
    winner_player_id: str


# Union type for all event types (used in results field for OpenAPI)
GameEvent = Union[
    GameStart,
    RoundStart,
    Bid,
    SelectTrump,
    Discard,
    TrickStart,
    PlayEvent,
    TrickEnd,
    RoundEnd,
    GameEnd,
]


class Play(BaseModel):
    """A class to model the client format of a Hundred and Ten play"""

    player_id: str
    card: Card


class Trick(BaseModel):
    """A class to model the client format of a Hundred and Ten trick"""

    bleeding: bool
    plays: list[Play]
    winning_play: Optional[Play] = None


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
    results: list[GameEvent]


class CompletedGame(Game):
    """A class to model the client format of a completed Hundred and Ten game"""

    winner: PlayerInGame
    organizer: PlayerInGame
    players: list[PlayerInGame]
    scores: dict[str, int]
    results: list[GameEvent]


class Suggestion(BaseModel):
    """A class to act as a superclass for suggested actions to the client"""


class BidSuggestion(Suggestion):
    """A class to model a suggested bid action to the client"""

    type: Literal["BID"] = "BID"
    amount: int


class SelectTrumpSuggestion(Suggestion):
    """A class to model a suggested trump selection action to the client"""

    type: Literal["SELECT_TRUMP"] = "SELECT_TRUMP"
    suit: SelectableSuit


class DiscardSuggestion(Suggestion):
    """A class to model a suggested discard action to the client"""

    type: Literal["DISCARD"] = "DISCARD"
    cards: list[Card]


class PlaySuggestion(Suggestion):
    """A class to model a suggested play action to the client"""

    type: Literal["PLAY"] = "PLAY"
    card: Card


# Union type for all suggestion types (used in response_model for OpenAPI)
SuggestionResponse = Union[
    BidSuggestion, SelectTrumpSuggestion, DiscardSuggestion, PlaySuggestion
]
