"""Identity model for authenticated requests"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Identity:
    """Represents an authenticated user's identity"""

    id: str
