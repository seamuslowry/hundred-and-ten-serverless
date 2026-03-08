"""Init the repository module"""

from .mongo import game_client, lobby_client, user_client

__all__ = ["game_client", "lobby_client", "user_client"]
