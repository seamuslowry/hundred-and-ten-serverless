'''
Endpoint to join a 110 game
'''
import json

import azure.functions as func

from utils.decorators import catcher
from utils.mappers.client import serialize
from utils.parsers import parse_request
from utils.services import GameService

bp = func.Blueprint()


@bp.function_name("join_game")
@bp.route(route="join/{game_id}", methods=["POST"])
@catcher
def join_game(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Join a 110 game
    '''
    identifier, game = parse_request(req)
    game.join(identifier)
    game = GameService.save(game)

    return func.HttpResponse(json.dumps(serialize.game(game, identifier)))
