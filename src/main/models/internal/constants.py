"""App-level constants removed from hundredandten v2"""

from enum import Enum, IntEnum


class BidAmount(IntEnum):
    """Valid bid amount"""

    PASS = 0
    FIFTEEN = 15
    TWENTY = 20
    TWENTY_FIVE = 25
    THIRTY = 30
    SHOOT_THE_MOON = 60


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
    FOUR = "FOUR"
    EIGHT = "EIGHT"
    SEVEN = "SEVEN"
    SIX = "SIX"
    THREE = "THREE"
    TWO = "TWO"
