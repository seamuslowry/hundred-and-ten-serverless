"""Format of a games of Hundred and Ten in the DB"""

from abc import ABC
from enum import Enum

from beanie import Document

from .player import PlayerInGame


class Accessibility(Enum):
    """An enum representing the accessibility of a lobby"""

    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"


class Lobby(ABC, Document):
    """A base class for lobbies"""

    class Settings:
        """Settings for the base lobby beanie model"""

        is_root = True
        name = "lobbies"  # the collection
        class_id = "schema_version"  # the field to discriminate on

    name: str
    accessibility: Accessibility
    organizer: PlayerInGame
    players: list[PlayerInGame]
    invitees: list[PlayerInGame]


class LobbyV0(Lobby):
    """A V0 lobby document"""
