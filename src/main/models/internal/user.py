"""Model user-related information."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    """A class to interact with generic users"""

    player_id: str
    name: Optional[str] = None
    id: Optional[str] = None
    picture_url: Optional[str] = None
