"""Internal models for tricks"""

from dataclasses import dataclass

from .actions import Play


@dataclass
class Trick:
    """Internal representation of a trick"""

    bleeding: bool
    winning_play: Play | None
    plays: list[Play]
