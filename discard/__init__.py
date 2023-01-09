'''
Endpoint to discard cards in a 110 game
'''
import json

import azure.functions as func

from app.decorators import catcher
from app.mappers.client import deserialize, serialize
from app.models import Discard
from app.parsers import parse_request
from app.services import GameService


@catcher
def main(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Discard in a 110 game
    '''
    user, game = parse_request(req)
    initial_event_knowledge = len(game.events)

    body = req.get_json()

    game.act(Discard(user.identifier, [deserialize.card(c) for c in body.get('cards')]))

    game = GameService.save(game)

    return func.HttpResponse(
        json.dumps(serialize.game(game, user.identifier, initial_event_knowledge)))
