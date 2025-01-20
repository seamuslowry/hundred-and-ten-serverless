'''
Endpoint to discard cards in a 110 game
'''
import json

import azure.functions as func

from utils.decorators import catcher
from utils.mappers.client import deserialize, serialize
from utils.models import Discard
from utils.parsers import parse_request
from utils.services import GameService

bp = func.Blueprint()


@bp.function_name("discard")
@bp.route(route="discard/{game_id}", methods=["POST"])
@catcher
def discard(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Discard in a 110 game
    '''
    identifier, game = parse_request(req)
    initial_event_knowledge = len(game.events)

    body = req.get_json()

    game.act(Discard(identifier, [deserialize.card(c) for c in body.get('cards')]))

    game = GameService.save(game)

    return func.HttpResponse(
        json.dumps(serialize.game(game, identifier, initial_event_knowledge)))
