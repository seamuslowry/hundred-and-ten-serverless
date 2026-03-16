"""Model user-related information."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class User:
    """A class to interact with generic users"""

    player_id: str
    name: str = field(compare=False)
    id: Optional[str] = None
    picture_url: Optional[str] = field(compare=False, default=None)
