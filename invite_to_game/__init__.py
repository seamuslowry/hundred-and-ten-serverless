'''
Endpoint to invite players to a 110 game
'''
import json

import azure.functions as func

from app.decorators import catcher
from app.mappers.client import serialize
from app.parsers import parse_request
from app.services import GameService


@catcher
def main(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Invite to join a 110 game
    '''
    user, game = parse_request(req)

    body = req.get_json()
    invitees = body.get('invitees', [])

    for invitee in invitees:
        game.invite(user.identifier, invitee)
    game = GameService.save(game)

    return func.HttpResponse(json.dumps(serialize.game(game, user.identifier)))
