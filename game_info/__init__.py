'''
Endpoint to retrieve a game
'''
import json

import azure.functions as func

from app.decorators import catcher
from app.parsers import parse_request
from app.services import GameService


@catcher
def main(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Retrieve 110 game.
    '''
    user, game = parse_request(req)

    return func.HttpResponse(json.dumps(GameService.json(game, user.identifier)))
