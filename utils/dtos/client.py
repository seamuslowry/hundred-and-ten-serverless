'''Format of a game of Hundred and Ten on the client'''

from typing import Optional, TypedDict, Union


class User(TypedDict):
    '''A class to model the client format of a Hundred and Ten user'''
    identifier: str
    name: str
    picture_url: Optional[str]


class Person(TypedDict):
    '''A class to model the client format of a Hundred and Ten person'''
    identifier: str
    automate: bool
    prepassed: bool


class OtherPlayer(Person):
    '''A class to model the client format of a Hundred and Ten player'''
    hand_size: int


class Card(TypedDict):
    '''A class to model the client format of a Hundred and Ten card'''
    suit: str
    number: str


class Self(Person):
    '''A class to model the client format of the logged in Hundred and Ten player'''
    hand: list[Card]


Player = Union[Self, OtherPlayer]


class Event(TypedDict):
    '''A class to model the client format of a Hundred and Ten event'''
    type: str


class GameStart(Event):
    '''A class to model the client format of a Hundred and Ten game start event'''


class RoundStart(Event):
    '''A class to model the client format of a Hundred and Ten round start event'''
    dealer: str
    hands: dict[str, Union[list[Card], int]]


class Bid(Event):
    '''A class to model the client format of a Hundred and Ten bid event'''
    identifier: str
    amount: int


class SelectTrump(Event):
    '''A class to model the client format of a Hundred and Ten select trump event'''
    identifier: str
    suit: str


class Discard(Event):
    '''A class to model the client format of a Hundred and Ten discard event'''
    identifier: str
    discards: Union[list[Card], int]


class TrickStart(Event):
    '''A class to model the client format of a Hundred and Ten trick start event'''


class PlayEvent(Event):
    '''A class to model the client format of a Hundred and Ten play event'''
    identifier: str
    card: Card


class TrickEnd(Event):
    '''A class to model the client format of a Hundred and Ten trick end event'''
    winner: str


class RoundEnd(Event):
    '''A class to model the client format of a Hundred and Ten round end event'''
    scores: dict[str, int]


class GameEnd(Event):
    '''A class to model the client format of a Hundred and Ten game end event'''
    winner: str


class Play(TypedDict):
    '''A class to model the client format of a Hundred and Ten play'''
    identifier: str
    card: Card


class Trick(TypedDict):
    '''A class to model the client format of a Hundred and Ten trick'''
    bleeding: bool
    plays: list[Play]
    winning_play: Optional[Play]


class Round(TypedDict):
    '''A class to model the client format of a Hundred and Ten round'''
    players: list[Player]
    dealer: Player
    bidder: Optional[Player]
    bid: Optional[int]
    trump: Optional[str]
    tricks: list[Trick]
    active_player: Optional[Player]


class Game(TypedDict):
    '''A class to model the client format of a Hundred and Ten game'''
    id: str
    name: str
    status: str


class WaitingGame(Game):
    '''A class to model the client format of a waiting Hundred and Ten game'''
    accessibility: str
    organizer: Person
    players: list[Person]
    invitees: list[Person]


class StartedGame(Game):
    '''A class to model the client format of a started Hundred and Ten game'''
    round: Round
    scores: dict[str, int]
    results: Optional[list[Event]]


class CompletedGame(Game):
    '''A class to model the client format of a completed Hundred and Ten game'''
    winner: Person
    organizer: Person
    players: list[Person]
    scores: dict[str, int]
    results: Optional[list[Event]]


class Suggestion(TypedDict):
    '''A class to act as a superclass for suggestioned actions to the client'''


class BidSuggestion(Suggestion):
    '''A class to model a suggested bid action to the client'''
    amount: int


class SelectTrumpSuggestion(Suggestion):
    '''A class to model a suggested trump selection action to the client'''
    suit: str


class DiscardSuggestion(Suggestion):
    '''A class to model a suggested discard action to the client'''
    cards: list[Card]


class PlaySuggestion(Suggestion):
    '''A class to model a suggested play action to the client'''
    card: Card
