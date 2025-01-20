'''
Endpoint to select trump in a 110 game
'''
import json

import azure.functions as func

from utils.decorators import catcher
from utils.mappers.client import serialize
from utils.models import SelectableSuit, SelectTrump
from utils.parsers import parse_request
from utils.services import GameService


bp = func.Blueprint()


@bp.function_name("select_trump")
@bp.route(route="select/{game_id}", methods=["POST"])
@catcher
def select_trump(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Select trump in a 110 game
    '''
    identifier, game = parse_request(req)
    initial_event_knowledge = len(game.events)

    body = req.get_json()

    game.act(SelectTrump(identifier, SelectableSuit[body['suit']]))

    game = GameService.save(game)

    return func.HttpResponse(
        json.dumps(serialize.game(game, identifier, initial_event_knowledge)))
