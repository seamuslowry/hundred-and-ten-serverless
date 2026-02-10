"""App-level Person class for lobby phase management"""

from dataclasses import dataclass, field


@dataclass
class Person:
    """A person in the lobby phase of a game"""

    identifier: str
    automate: bool = field(compare=False, default=False)
