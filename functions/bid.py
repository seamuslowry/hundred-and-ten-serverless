'''
Endpoint to place a bid in a 110 game
'''
import json

import azure.functions as func

from utils.decorators import catcher
from utils.mappers.client import serialize
from utils.models import Bid, BidAmount
from utils.parsers import parse_request
from utils.services import GameService

bp = func.Blueprint()


@bp.function_name("bid")
@bp.route(route="bid/{game_id}", methods=["POST"])
@catcher
def bid(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Bid in a 110 game
    '''
    identifier, game = parse_request(req)
    initial_event_knowledge = len(game.events)

    body = req.get_json()

    game.act(Bid(identifier, BidAmount(body['amount'])))

    game = GameService.save(game)

    return func.HttpResponse(json.dumps(
        serialize.game(
            game,
            identifier,
            initial_event_knowledge)))
