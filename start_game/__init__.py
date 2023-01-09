'''
Endpoint to start a 110 game
'''
import json

import azure.functions as func

from app.decorators import catcher
from app.mappers.client import serialize
from app.models import HundredAndTenError
from app.parsers import parse_request
from app.services import GameService

MIN_PLAYERS = 4


@catcher
def main(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Start a 110 game
    '''
    user, game = parse_request(req)

    if user.identifier != game.organizer.identifier:
        raise HundredAndTenError("Only the organizer can start the game")

    for num in range(len(game.players), MIN_PLAYERS):
        cpu_identifier = str(num + 1)
        game.invite(user.identifier, cpu_identifier)
        game.join(cpu_identifier)
        game.automate(cpu_identifier)

    game.start_game()

    game = GameService.save(game)

    return func.HttpResponse(json.dumps(serialize.game(game, user.identifier, 0)))
