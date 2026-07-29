"""Init the routers module"""

from .games import router as games
from .lobbies import router as lobbies
from .players import router as players

__all__ = ["games", "lobbies", "players"]
