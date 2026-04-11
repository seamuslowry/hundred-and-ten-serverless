"""App-level Player class"""

from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Self

from .actions import Action, Card


# ---------------------------------------------------------------------------
# ActionRequest discriminated union
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NoAction:
    """Sentinel: the player has no action to take right now."""


@dataclass(frozen=True)
class ConcreteAction:
    """Wraps a concrete action that should be played immediately."""

    action: Action


@dataclass(frozen=True)
class RequestAutomation:
    """Sentinel: the player defers to automated action resolution (CPU)."""


type ActionRequest = NoAction | ConcreteAction | RequestAutomation


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
    def next_action(self) -> ActionRequest:
        """Return the next action for this player, or a sentinel indicating intent."""


@dataclass
class Human(PlayerInGame):
    """A human; represents a real user that will provide input"""

    queued_actions: deque[Action] = field(default_factory=deque)

    def next_action(self) -> ActionRequest:
        if not self.queued_actions:
            return NoAction()
        return ConcreteAction(self.queued_actions.popleft())

    def queue_action(self, action: Action) -> Self:
        self.queued_actions.append(action)
        return self

    def clear_queued_actions(self) -> Self:
        self.queued_actions.clear()
        return self


@dataclass
class NaiveCpu(PlayerInGame):
    """A naive CPU using the built-in automated player"""

    def next_action(self) -> ActionRequest:
        return RequestAutomation()


@dataclass
class PlayerInRound:
    """A player in a round"""

    id: str
    hand: list[Card]
