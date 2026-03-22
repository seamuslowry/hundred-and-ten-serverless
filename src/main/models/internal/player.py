"""App-level Player class"""

from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Optional, Self

from hundredandten import actions, player, state

from src.main.models.internal.errors import BadRequestException


@dataclass
class QueuedActionPlayer(player.AutomatedPlayer):
    """Represent a player with queued actions to be played in FIFO order."""

    on_consume_actions: Callable[[list[actions.Action]], None]
    queued_actions: deque[actions.Action] = field(default_factory=deque)

    def act(self, game_state: state.GameState) -> Optional[actions.Action]:
        """Return the earliest queued action if it is available, dropping any expired ones."""
        if not self.queued_actions:
            return None

        action = self.queued_actions.popleft()

        if action in game_state.available_actions:
            self.on_consume_actions([action])
            return action

        # Invalid → flush entire queue (including this action)
        self.queued_actions.clear()
        self.on_consume_actions([action, *self.queued_actions])

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
    def queue_action(self, action: actions.Action) -> Self:
        """Attempt to queue an action for the player"""

    @abstractmethod
    def clear_queued_actions(self) -> Self:
        """Clear all queued actions for the player"""

    @abstractmethod
    def as_engine_player(self) -> player.Player:
        """Return this player as an engine player"""


@dataclass
class Human(PlayerInGame):
    """A human; represents a real user that will provide input"""

    queued_actions: list[actions.Action] = field(default_factory=list)

    def queue_action(self, action: actions.Action) -> Self:
        self.queued_actions.append(action)
        return self

    def clear_queued_actions(self) -> Self:
        self.queued_actions.clear()
        return self

    def as_engine_player(self) -> player.Player:
        return QueuedActionPlayer(
            self.id,
            queued_actions=deque(self.queued_actions),
            on_consume_actions=lambda consumed: setattr(
                self,
                "queued_actions",
                [action for action in self.queued_actions if action not in consumed],
            ),
        )


@dataclass
class NaiveCpu(PlayerInGame):
    """A naive CPU using the built-in automated player"""

    def queue_action(self, action: actions.Action) -> Self:
        raise BadRequestException("Cannot queue an action for an automated player")

    def clear_queued_actions(self) -> Self:
        raise BadRequestException("Cannot queue actions for an automated player")

    def as_engine_player(self) -> player.Player:
        return player.NaiveAutomatedPlayer(self.id)
