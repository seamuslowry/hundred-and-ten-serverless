'''
Endpoint to play a card in a 110 game
'''
import json

import azure.functions as func

from utils.decorators import catcher
from utils.mappers.client import serialize
from utils.parsers import parse_request

bp = func.Blueprint()


@bp.function_name("suggestion")
@bp.route(route="suggestion/{game_id}", methods=["POST"])
@catcher
def suggestion(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Ask for a suggestion in a 110 game
    '''
    identifier, game = parse_request(req)

    return func.HttpResponse(
        json.dumps(serialize.suggestion(game.suggestion(), identifier)))
