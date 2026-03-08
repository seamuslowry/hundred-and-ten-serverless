"""App-level Person class for lobby phase management"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from hundredandten.player import HumanPlayer, NaiveAutomatedPlayer, Player


@dataclass
class Person(ABC):
    """A person in a game"""

    identifier: str

    @abstractmethod
    def as_player(self) -> Player:
        """Return this person as a player in a game"""


@dataclass
class Human(Person):
    """A human; represents a real user that will provide input"""

    def as_player(self) -> Player:
        return HumanPlayer(self.identifier)


@dataclass
class NaiveCpu(Person):
    """A naive CPU; uses the naive automated player from hundredandten"""

    def as_player(self) -> Player:
        return NaiveAutomatedPlayer(self.identifier)
