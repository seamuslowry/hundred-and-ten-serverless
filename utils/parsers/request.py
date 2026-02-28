"""
Parse models off an HTTP request
"""

from typing import Tuple

import azure.functions as func

from utils.mappers.client import deserialize
from utils.models import Game, Lobby
from utils.services import GameService, LobbyService


def parse_lobby_request(req: func.HttpRequest) -> Tuple[str, Lobby]:
    """
    Parse the request for a lobby
    """
    lobby_id = req.route_params.get("lobby_id", "")
    lobby = LobbyService.get(lobby_id)

    return (deserialize.user_id(), lobby)


def parse_game_request(req: func.HttpRequest) -> Tuple[str, Game]:
    """
    Parse the request for a game
    """
    game_id = req.route_params.get("game_id", "")
    game = GameService.get(game_id)

    return (deserialize.user_id(), game)
