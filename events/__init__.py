'''
Endpoint to retrieve all events a game
'''
import json

import azure.functions as func

from app.decorators import catcher
from app.mappers.client import serialize
from app.parsers import parse_request


@catcher
def main(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Retrieve events on a 110 game.
    '''
    user, game = parse_request(req)

    return func.HttpResponse(
        json.dumps(serialize.events(game.events, user.identifier)))
