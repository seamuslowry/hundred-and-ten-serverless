'''
Endpoint to play a card in a 110 game
'''
import json

import azure.functions as func

from app.decorators import catcher
from app.mappers.client import serialize
from app.parsers import parse_request


@catcher
def main(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Ask for a suggestion in a 110 game
    '''
    user, game = parse_request(req)

    return func.HttpResponse(
        json.dumps(serialize.suggestion(game.suggestion(), user.identifier)))
