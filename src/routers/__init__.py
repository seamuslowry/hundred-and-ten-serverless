"""Init the routers module"""

from .games import router as games
from .lobbies import router as lobbies
from .players import router as players

__all__ = ["players", "lobbies", "games"]
