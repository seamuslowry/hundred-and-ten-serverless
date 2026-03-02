"""Format of a game of Hundred and Ten on the client"""

from typing import Optional, Union

from pydantic import BaseModel, Field


class User(BaseModel):
    """A class to model the client format of a Hundred and Ten user"""

    identifier: str
    name: str
    picture_url: Optional[str] = None


class Person(BaseModel):
    """A class to model the client format of a Hundred and Ten person"""

    identifier: str
    automate: bool


class OtherPlayer(Person):
    """A class to model the client format of a Hundred and Ten player"""

    hand_size: int


class Card(BaseModel):
    """A class to model the client format of a Hundred and Ten card"""

    suit: str
    number: str


class Self(BaseModel):
    """A class to model the client format of the logged in Hundred and Ten player"""

    identifier: str
    automate: bool
    hand: list[Card]
    prepassed: bool


Player = Union[Self, OtherPlayer]


# =============================================================================
# Event types
# =============================================================================


class Event(BaseModel):
    """A class to model the client format of a Hundred and Ten event"""

    type: str


class GameStart(Event):
    """A class to model the client format of a Hundred and Ten game start event"""

    pass


class RoundStart(Event):
    """A class to model the client format of a Hundred and Ten round start event"""

    dealer: str
    hands: dict[str, Union[list[Card], int]]


class Bid(BaseModel):
    """A class to model the client format of a Hundred and Ten bid event"""

    type: str = Field(default="Bid")
    identifier: str
    amount: int


class SelectTrump(BaseModel):
    """A class to model the client format of a Hundred and Ten select trump event"""

    type: str = Field(default="SelectTrump")
    identifier: str
    suit: str


class Discard(BaseModel):
    """A class to model the client format of a Hundred and Ten discard event"""

    type: str = Field(default="Discard")
    identifier: str
    discards: Union[list[Card], int]


class TrickStart(Event):
    """A class to model the client format of a Hundred and Ten trick start event"""

    pass


class PlayEvent(BaseModel):
    """A class to model the client format of a Hundred and Ten play event"""

    type: str = Field(default="Play")
    identifier: str
    card: Card


class TrickEnd(BaseModel):
    """A class to model the client format of a Hundred and Ten trick end event"""

    type: str = Field(default="TrickEnd")
    winner: str


class Score(BaseModel):
    """A class to model the client format of a score in a Hundred and Ten round end event"""

    identifier: str
    value: int


class RoundEnd(BaseModel):
    """A class to model the client format of a Hundred and Ten round end event"""

    type: str = Field(default="RoundEnd")
    scores: list[Score]


class GameEnd(BaseModel):
    """A class to model the client format of a Hundred and Ten game end event"""

    type: str = Field(default="GameEnd")
    winner: str


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

    identifier: str
    card: Card


class Trick(BaseModel):
    """A class to model the client format of a Hundred and Ten trick"""

    bleeding: bool
    plays: list[Play]
    winning_play: Optional[Play] = None


class Round(BaseModel):
    """A class to model the client format of a Hundred and Ten round"""

    players: list[Player]
    dealer: Player
    bidder: Optional[Player] = None
    bid: Optional[int] = None
    trump: Optional[str] = None
    tricks: list[Trick]
    active_player: Optional[Player] = None


class Game(BaseModel):
    """A class to model the client format of a Hundred and Ten game"""

    id: str
    name: str
    status: str


class WaitingGame(Game):
    """A class to model the client format of a waiting Hundred and Ten game"""

    accessibility: str
    organizer: Person
    players: list[Person]
    invitees: list[Person]


class StartedGame(Game):
    """A class to model the client format of a started Hundred and Ten game"""

    round: Optional[Round] = None
    scores: dict[str, int]
    results: Optional[list[GameEvent]] = None


class CompletedGame(Game):
    """A class to model the client format of a completed Hundred and Ten game"""

    winner: Person
    organizer: Person
    players: list[Person]
    scores: dict[str, int]
    results: Optional[list[GameEvent]] = None


class Suggestion(BaseModel):
    """A class to act as a superclass for suggested actions to the client"""

    pass


class BidSuggestion(Suggestion):
    """A class to model a suggested bid action to the client"""

    amount: int


class SelectTrumpSuggestion(Suggestion):
    """A class to model a suggested trump selection action to the client"""

    suit: str


class DiscardSuggestion(Suggestion):
    """A class to model a suggested discard action to the client"""

    cards: list[Card]


class PlaySuggestion(Suggestion):
    """A class to model a suggested play action to the client"""

    card: Card


# Union type for all suggestion types (used in response_model for OpenAPI)
SuggestionResponse = Union[
    BidSuggestion, SelectTrumpSuggestion, DiscardSuggestion, PlaySuggestion
]
