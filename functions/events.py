'''
Endpoint to retrieve all events a game
'''
import json

import azure.functions as func

from utils.decorators import catcher
from utils.mappers.client import serialize
from utils.parsers import parse_request

bp = func.Blueprint()


@bp.function_name("events")
@bp.route(route="events/{game_id}", methods=["POST"])
@catcher
def events(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Retrieve events on a 110 game.
    '''
    identifier, game = parse_request(req)

    return func.HttpResponse(
        json.dumps(serialize.events(game.events, identifier)))
