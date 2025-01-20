'''
Endpoint to play a card in a 110 game
'''
import json

import azure.functions as func

from utils.decorators import catcher
from utils.mappers.client import deserialize, serialize
from utils.models import Play
from utils.parsers import parse_request
from utils.services import GameService

bp = func.Blueprint()


@bp.function_name("play")
@bp.route(route="play/{game_id}", methods=["POST"])
@catcher
def play(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Play a card in a 110 game
    '''
    identifier, game = parse_request(req)
    initial_event_knowledge = len(game.events)

    body = req.get_json()

    game.act(Play(identifier, deserialize.card(body.get('card'))))

    game = GameService.save(game)

    return func.HttpResponse(
        json.dumps(serialize.game(game, identifier, initial_event_knowledge)))
