'''
Endpoint to leave a 110 game
'''
import json

import azure.functions as func

from utils.decorators import catcher
from utils.mappers.client import serialize
from utils.models import RoundStatus
from utils.parsers import parse_request
from utils.services import GameService

bp = func.Blueprint()


@bp.function_name("leave_game")
@bp.route(route="leave/{game_id}", methods=["POST"])
@catcher
def leave_game(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Leave a 110 game
    '''
    identifier, game = parse_request(req)
    initial_event_knowledge = len(game.events)
    if isinstance(game.status, RoundStatus):
        game.automate(identifier)
    else:
        game.leave(identifier)
    game = GameService.save(game)

    return func.HttpResponse(
        json.dumps(serialize.game(game, identifier, initial_event_knowledge)))
