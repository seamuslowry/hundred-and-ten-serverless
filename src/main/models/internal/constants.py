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
