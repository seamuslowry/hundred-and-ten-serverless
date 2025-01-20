'''
Endpoint to retrieve user info of players on a game
'''
import json

import azure.functions as func

from utils.decorators import catcher
from utils.mappers.client import serialize
from utils.parsers import parse_request
from utils.services import UserService

bp = func.Blueprint()


@bp.function_name("players")
@bp.route(route="players/{game_id}", methods=["GET"])
@catcher
def players(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Retrieve players on a 110 game.
    '''
    _, game = parse_request(req)

    people_ids = list(map(lambda p: p.identifier, game.people))

    return func.HttpResponse(
        json.dumps(list(map(serialize.user, UserService.by_identifiers(people_ids)))))
