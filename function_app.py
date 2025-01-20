'''
The entrypoint for azure functions
'''
import json
import azure.functions as func

from utils.decorators import catcher
from utils.mappers.client import serialize
from utils.models import Bid, BidAmount
from utils.parsers import parse_request
from utils.services import GameService

from functions.create_game import bp as create_game_bp
from functions.discard import bp as discard_bp
from functions.events import bp as events_bp
from functions.game_info import bp as game_info_bp
from functions.invite_to_game import bp as invite_to_game_bp
from functions.join_game import bp as join_game_bp
from functions.leave_game import bp as leave_game_bp
from functions.play import bp as play_bp
from functions.players import bp as players_bp
from functions.rescind_prepass import bp as rescind_prepass_bp
from functions.search_games import bp as search_games_bp
from functions.search_users import bp as search_users_bp
from functions.select_trump import bp as select_trump_bp
from functions.self import bp as self_bp
from functions.start_game import bp as start_game_bp
from functions.suggestion import bp as suggestion_bp

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.function_name("bid")
@app.route(route="bid/{game_id}", methods=["POST"])
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


app.register_functions(create_game_bp)
app.register_functions(discard_bp)
app.register_functions(events_bp)
app.register_functions(game_info_bp)
app.register_functions(invite_to_game_bp)
app.register_functions(join_game_bp)
app.register_functions(leave_game_bp)
app.register_functions(play_bp)
app.register_functions(players_bp)
app.register_functions(rescind_prepass_bp)
app.register_functions(search_games_bp)
app.register_functions(search_users_bp)
app.register_functions(select_trump_bp)
app.register_functions(self_bp)
app.register_functions(start_game_bp)
app.register_functions(suggestion_bp)
