"""App-level Player class"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional, Self

from hundredandten import actions, player, state

from src.main.models.internal.errors import BadRequestException


@dataclass
class QueuedActionPlayer(player.AutomatedPlayer):
    """Represent a player with a single queued action."""

    on_action: Callable[[], None]
    queued_action: Optional[actions.Action] = None

    def act(self, game_state: state.GameState) -> Optional[actions.Action]:
        """Return the queued action if available"""
        action = self.queued_action
        self.queued_action = None
        self.on_action()
        if action in game_state.available_actions:
            return action
        return None


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
    def queue_action(self, action: Optional[actions.Action]) -> Self:
        """Attempt to queue an action for the player"""

    @abstractmethod
    def as_engine_player(self) -> player.Player:
        """Return this player as an engine player"""


@dataclass
class Human(PlayerInGame):
    """A human; represents a real user that will provide input"""

    queued_action: Optional[actions.Action] = None

    def queue_action(self, action: Optional[actions.Action]) -> Self:
        self.queued_action = action
        return self

    def as_engine_player(self) -> player.Player:
        return QueuedActionPlayer(
            self.id,
            queued_action=self.queued_action,
            on_action=lambda: setattr(self, "queued_action", None),
        )


@dataclass
class NaiveCpu(PlayerInGame):
    """A naive CPU using the built-in automated player"""

    def queue_action(self, action: Optional[actions.Action]) -> Self:
        raise BadRequestException("Cannot queue an action for an automated player")

    def as_engine_player(self) -> player.Player:
        return player.NaiveAutomatedPlayer(self.id)
