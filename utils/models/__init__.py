"""Init the models module"""

# App-level types (removed from hundredandten v2)
# Import from hundredandten v2
from hundredandten import HundredAndTen
from hundredandten.actions import (
    Action,
    Bid,
    DetailedDiscard,
    Discard,
    Play,
    SelectTrump,
    Unpass,
)
from hundredandten.constants import (
    BidAmount,
    CardNumber,
    RoundRole,
    RoundStatus,
    SelectableSuit,
    UnselectableSuit,
)
from hundredandten.deck import Card, Deck
from hundredandten.events import (
    Event,
    GameEnd,
    GameStart,
    RoundEnd,
    RoundStart,
    TrickEnd,
    TrickStart,
)
from hundredandten.group import Group, Player, RoundPlayer
from hundredandten.hundred_and_ten_error import HundredAndTenError
from hundredandten.round import Round
from hundredandten.trick import Trick

from utils.constants import Accessibility, GameRole, GameStatus
from utils.models.game import Game
from utils.models.lobby import Lobby, PersonGroup
from utils.models.person import Person
from utils.models.user import User

__all__ = [
    # hundredandten v2
    "HundredAndTen",
    # Actions
    "Action",
    "Bid",
    "DetailedDiscard",
    "Discard",
    "Play",
    "SelectTrump",
    "Unpass",
    # Constants
    "BidAmount",
    "CardNumber",
    "RoundRole",
    "RoundStatus",
    "SelectableSuit",
    "UnselectableSuit",
    # Deck
    "Card",
    "Deck",
    # Events
    "Event",
    "GameEnd",
    "GameStart",
    "RoundEnd",
    "RoundStart",
    "TrickEnd",
    "TrickStart",
    # Group
    "Group",
    "Player",
    "RoundPlayer",
    # Error
    "HundredAndTenError",
    # Round
    "Round",
    # Trick
    "Trick",
    # Utils constants
    "Accessibility",
    "GameRole",
    "GameStatus",
    # Utils models
    "Game",
    "Lobby",
    "PersonGroup",
    "Person",
    "User",
]
