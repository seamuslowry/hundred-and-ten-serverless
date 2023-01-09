'''
Endpoint to leave a 110 game
'''
import json

import azure.functions as func

from app.decorators import catcher
from app.mappers.client import serialize
from app.models import RoundStatus
from app.parsers import parse_request
from app.services import GameService


@catcher
def main(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Leave a 110 game
    '''
    user, game = parse_request(req)
    if isinstance(game.status, RoundStatus):
        game.automate(user.identifier)
    else:
        game.leave(user.identifier)
    game = GameService.save(game)

    return func.HttpResponse(json.dumps(serialize.game(game, user.identifier)))
