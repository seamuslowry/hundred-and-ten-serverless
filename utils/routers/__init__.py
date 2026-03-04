"""Init the routers module"""

from utils.routers.games import router as games
from utils.routers.lobbies import router as lobbies
from utils.routers.users import router as users

__all__ = ["users", "lobbies", "games"]
