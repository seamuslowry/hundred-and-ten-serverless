"""Identity model for authenticated requests"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Identity:
    """Represents an authenticated user's identity"""

    id: str
    name: str | None = None
    picture_url: str | None = None
