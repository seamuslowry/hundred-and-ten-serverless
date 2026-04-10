"""Identity model for authenticated requests"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Identity:
    """Represents an authenticated user's identity"""

    id: str
    name: Optional[str] = None
    picture_url: Optional[str] = None
