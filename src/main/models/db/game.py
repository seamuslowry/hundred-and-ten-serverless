"""Format of a games of Hundred and Ten in the DB"""


from abc import ABC
from typing import Optional

from beanie import Document, UnionDoc

from .move import Move

from .player import Player


class BaseGame(ABC, UnionDoc):
    """A base class for games"""
    class Settings:
        """Settings for this beanie model"""
        name = "games"  # the collection
        class_id = "schema_version"  # the field to discriminate on


class GameV0(Document):
    """A V0 game document"""
    class Settings:
        """Settings for the V0 game document"""
        union_doc = BaseGame
        name = "v0"

    name: str
    seed: str
    organizer: Player
    players: list[Player]
    winner: Optional[str]
    active_player: str
    status: str
    moves: list[Move]
