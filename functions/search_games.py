'''
Endpoint to get games from the DB
'''
import json

import azure.functions as func

from utils.decorators import catcher
from utils.dtos.db import SearchGame
from utils.mappers.client import serialize
from utils.parsers import parse_request
from utils.services import GameService

bp = func.Blueprint()


@bp.function_name("search_games")
@bp.route(route="games", methods=["GET"])
@catcher
def search_games(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Get games
    '''
    identifier, *_ = parse_request(req)

    body = req.get_json()
    max_count = body.get('max', 20)

    return func.HttpResponse(
        json.dumps(
            list(map(lambda g: serialize.game(g, identifier),
                     GameService.search(SearchGame(
                         name=body.get('searchText', ''),
                         client=identifier,
                         statuses=body.get('statuses', None),
                         active_player=body.get('activePlayer', None),
                         winner=body.get('winner', None)
                     ), max_count)))))
