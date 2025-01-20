'''
Endpoint to retrieve a game
'''
import json

import azure.functions as func

from utils.decorators import catcher
from utils.mappers.client import serialize
from utils.parsers import parse_request

bp = func.Blueprint()


@bp.function_name("game_info")
@bp.route(route="info/{game_id}", methods=["POST"])
@catcher
def game_info(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Retrieve 110 game.
    '''
    identifier, game = parse_request(req)

    return func.HttpResponse(json.dumps(serialize.game(game, identifier)))
