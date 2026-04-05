"""Internal models for tricks"""

from dataclasses import dataclass
from typing import Optional

from .actions import Play


@dataclass
class Trick:
    """Internal representation of a trick"""

    bleeding: bool
    winning_play: Optional[Play]
    plays: list[Play]
