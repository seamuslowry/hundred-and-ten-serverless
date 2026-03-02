"""App-level constants removed from hundredandten v2"""

from enum import Enum


class Accessibility(str, Enum):
    """Visibility of a game"""

    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"


class GameStatus(str, Enum):
    """Status of a game at the app level (includes lobby phase)"""

    WAITING_FOR_PLAYERS = "WAITING_FOR_PLAYERS"
    PLAYING = "PLAYING"
    WON = "WON"


class Suit(str, Enum):
    """All card suits (selectable + unselectable) as string names for API"""

    HEARTS = "HEARTS"
    CLUBS = "CLUBS"
    SPADES = "SPADES"
    DIAMONDS = "DIAMONDS"
    JOKER = "JOKER"


class SelectableSuit(str, Enum):
    """Selectable trump suits as string names for API"""

    HEARTS = "HEARTS"
    CLUBS = "CLUBS"
    SPADES = "SPADES"
    DIAMONDS = "DIAMONDS"


class CardNumberName(str, Enum):
    """Card number names for API"""

    JOKER = "JOKER"
    TWO = "TWO"
    THREE = "THREE"
    FOUR = "FOUR"
    FIVE = "FIVE"
    SIX = "SIX"
    SEVEN = "SEVEN"
    EIGHT = "EIGHT"
    NINE = "NINE"
    TEN = "TEN"
    JACK = "JACK"
    QUEEN = "QUEEN"
    KING = "KING"
    ACE = "ACE"
