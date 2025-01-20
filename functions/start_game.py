'''
Endpoint to start a 110 game
'''
import json

import azure.functions as func

from utils.decorators import catcher
from utils.mappers.client import serialize
from utils.models import HundredAndTenError
from utils.parsers import parse_request
from utils.services import GameService

MIN_PLAYERS = 4

bp = func.Blueprint()


@bp.function_name("start_game")
@bp.route(route="start/{game_id}", methods=["POST"])
@catcher
def start_game(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Start a 110 game
    '''
    identifier, game = parse_request(req)

    if identifier != game.organizer.identifier:
        raise HundredAndTenError("Only the organizer can start the game")

    for num in range(len(game.players), MIN_PLAYERS):
        cpu_identifier = str(num + 1)
        game.invite(identifier, cpu_identifier)
        game.join(cpu_identifier)
        game.automate(cpu_identifier)

    game.start_game()

    game = GameService.save(game)

    return func.HttpResponse(json.dumps(serialize.game(game, identifier, 0)))
