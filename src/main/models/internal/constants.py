"""App-level constants removed from hundredandten v2"""

from enum import Enum


class Accessibility(str, Enum):
    """Visibility of a game"""

    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"


class GameStatus(str, Enum):
    """Status of a game"""

    BIDDING = "BIDDING"
    TRUMP_SELECTION = "TRUMP_SELECTION"
    TRICKS = "TRICKS"
    DISCARD = "DISCARD"
    WON = "WON"


class CardSuit(str, Enum):
    """Internal card suit model"""

    DIAMONDS = "DIAMONDS"
    SPADES = "SPADES"
    CLUBS = "CLUBS"
    HEARTS = "HEARTS"
    JOKER = "JOKER"


class CardNumber(str, Enum):
    """Internal card number model"""

    FIVE = "FIVE"
    JACK = "JACK"
    JOKER = "JOKER"
    ACE = "ACE"
    KING = "KING"
    QUEEN = "QUEEN"
    TEN = "TEN"
    NINE = "NINE"
    EIGHT = "EIGHT"
    SEVEN = "SEVEN"
    SIX = "SIX"
    FOUR = "FOUR"
    THREE = "THREE"
    TWO = "TWO"
