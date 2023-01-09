'''
Endpoint to get games from the DB
'''
import json

import azure.functions as func

from app.decorators import catcher
from app.dtos.db import SearchGame
from app.mappers.client import serialize
from app.parsers import parse_request
from app.services import GameService


@catcher
def main(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Get games
    '''
    user, *_ = parse_request(req)

    body = req.get_json()
    max_count = body.get('max', 20)

    return func.HttpResponse(
        json.dumps(
            list(map(lambda g: serialize.game(g, user.identifier),
                     GameService.search(SearchGame(
                         name=body.get('searchText', ''),
                         client=user.identifier,
                         statuses=body.get('statuses', None),
                         active_player=body.get('activePlayer', None),
                         winner=body.get('winner', None)
                     ), max_count)))))
