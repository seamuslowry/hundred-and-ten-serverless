"""Init the routers module"""

from utils.routers.games import router as games
from utils.routers.lobbies import router as lobbies
from utils.routers.players import router as players

__all__ = ["players", "lobbies", "games"]
