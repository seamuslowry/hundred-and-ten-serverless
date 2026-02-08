"""Init the service module"""

from utils.services import game as GameService
from utils.services import lobby as LobbyService
from utils.services import user as UserService

__all__ = ["GameService", "LobbyService", "UserService"]
