"""App-level Player class"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from hundredandten import player


@dataclass
class Player:
    """A class to interact with generic players"""

    player_id: str  # The external-facing identifier (will be firebase UID)
    name: Optional[str] = None

    id: Optional[str] = None  # The actual DB ID
    picture_url: Optional[str] = None


@dataclass
class PlayerInGame(ABC):
    """A player in a game"""

    id: str

    @abstractmethod
    def as_engine_player(self) -> player.Player:
        """Return this player as an engine player"""


@dataclass
class Human(PlayerInGame):
    """A human; represents a real user that will provide input"""

    def as_engine_player(self) -> player.Player:
        return player.HumanPlayer(self.id)


@dataclass
class NaiveCpu(PlayerInGame):
    """A naive CPU; uses the naive automated player from hundredandten"""

    def as_engine_player(self) -> player.Player:
        return player.NaiveAutomatedPlayer(self.id)
