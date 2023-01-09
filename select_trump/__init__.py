'''
Endpoint to select trump in a 110 game
'''
import json

import azure.functions as func

from app.decorators import catcher
from app.mappers.client import serialize
from app.models import SelectableSuit, SelectTrump
from app.parsers import parse_request
from app.services import GameService


@catcher
def main(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Select trump in a 110 game
    '''
    user, game = parse_request(req)
    initial_event_knowledge = len(game.events)

    body = req.get_json()

    game.act(SelectTrump(user.identifier, SelectableSuit[body['suit']]))

    game = GameService.save(game)

    return func.HttpResponse(
        json.dumps(serialize.game(game, user.identifier, initial_event_knowledge)))
