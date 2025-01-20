'''
Endpoint to undo a pre-pass in a 110 game
'''
import json

import azure.functions as func

from utils.decorators import catcher
from utils.mappers.client import serialize
from utils.models import Unpass
from utils.parsers import parse_request
from utils.services import GameService

bp = func.Blueprint()


@bp.function_name("rescind_prepass")
@bp.route(route="unpass/{game_id}", methods=["POST"])
@catcher
def rescind_prepass(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Unpass in a 110 game
    '''
    identifier, game = parse_request(req)
    initial_event_knowledge = len(game.events)

    game.act(Unpass(identifier))

    game = GameService.save(game)

    return func.HttpResponse(
        json.dumps(serialize.game(game, identifier, initial_event_knowledge)))
