'''
Endpoint to retrieve user info of players on a game
'''
import json

import azure.functions as func

from app.decorators import catcher
from app.mappers.client import serialize
from app.parsers import parse_request
from app.services import UserService


@catcher
def main(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Retrieve players on a 110 game.
    '''
    _, game = parse_request(req)

    people_ids = list(map(lambda p: p.identifier, game.people))

    return func.HttpResponse(
        json.dumps(list(map(serialize.user, UserService.by_identifiers(people_ids)))))
