"""Init the parsers module"""

from utils.parsers.request import parse as parse_request
from utils.parsers.request import parse_game_request, parse_lobby_request

__all__ = ["parse_game_request", "parse_lobby_request", "parse_request"]
