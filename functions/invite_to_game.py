'''
Endpoint to invite players to a 110 game
'''
import json

import azure.functions as func

from utils.decorators import catcher
from utils.mappers.client import serialize
from utils.parsers import parse_request
from utils.services import GameService

bp = func.Blueprint()


@bp.function_name("invite_to_game")
@bp.route(route="invite/{game_id}", methods=["POST"])
@catcher
def invite_to_game(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Invite to join a 110 game
    '''
    identifier, game = parse_request(req)

    body = req.get_json()
    invitees = body.get('invitees', [])

    for invitee in invitees:
        game.invite(identifier, invitee)
    game = GameService.save(game)

    return func.HttpResponse(json.dumps(serialize.game(game, identifier)))
