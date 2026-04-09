"""Format of a games of Hundred and Ten in the DB"""

from abc import ABC
from enum import Enum
from typing import Optional

from beanie import Document

from src.models.db.lobby import Accessibility

from .move import Move
from .player import PlayerInGame


class Status(Enum):
    """An enum representing the status of a game"""

    BIDDING = "BIDDING"
    TRUMP_SELECTION = "TRUMP_SELECTION"
    DISCARD = "DISCARD"
    TRICKS = "TRICKS"
    WON = "WON"


class Game(ABC, Document):
    """A base class for games"""

    class Settings:
        """Settings for the base game Beanie model"""

        is_root = True
        name = "games"  # the collection
        class_id = "schema_version"  # the field to discriminate on

    name: str
    seed: str
    organizer: PlayerInGame
    players: list[PlayerInGame]
    winner_player_id: Optional[str]
    active_player_id: Optional[str]
    status: Status
    moves: list[Move]
    accessibility: Accessibility


class GameV0(Game):
    """A V0 game document"""
