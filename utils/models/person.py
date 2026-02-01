"""App-level Person class for lobby phase management"""

from dataclasses import dataclass, field

from utils.constants import GameRole


@dataclass
class Person:
    """A person in the lobby phase of a game"""

    identifier: str
    roles: set[GameRole] = field(default_factory=set)
    automate: bool = False
