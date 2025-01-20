'''
The entrypoint for azure functions
'''
import json
import logging
import azure.functions as func

from utils.decorators import catcher
from utils.dtos.db import SearchGame
from utils.mappers.client import deserialize, serialize
from utils.models import (Accessibility, Bid, BidAmount,
                          Discard, Game, GameRole, HundredAndTenError,
                          Play, RoundStatus, SelectableSuit, SelectTrump,
                          Unpass)
from utils.parsers import parse_request
from utils.services import GameService, UserService

MIN_PLAYERS = 4

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


@app.function_name("create_game")
@app.route(route="create", methods=["POST"])
@catcher
def create_game(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Create a new 110 game.
    '''
    logging.info('Initiating create game request.')

    identifier, *_ = parse_request(req)

    logging.debug('Creating game for %s', identifier)

    body = req.get_json()

    game = Game()
    game.join(identifier)
    game.people.add_role(identifier, GameRole.ORGANIZER)
    game.name = body.get('name', f'{identifier} Game')
    game.accessibility = Accessibility[body.get('accessibility', Accessibility.PUBLIC.name)]

    game = GameService.save(game)

    logging.debug('Game %s created successfully', game.seed)

    return func.HttpResponse(json.dumps(serialize.game(game, identifier)))


@app.function_name("discard")
@app.route(route="discard/{game_id}", methods=["POST"])
@catcher
def discard(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Discard in a 110 game
    '''
    identifier, game = parse_request(req)
    initial_event_knowledge = len(game.events)

    body = req.get_json()

    game.act(Discard(identifier, [deserialize.card(c) for c in body.get('cards')]))

    game = GameService.save(game)

    return func.HttpResponse(
        json.dumps(serialize.game(game, identifier, initial_event_knowledge)))


@app.function_name("events")
@app.route(route="events/{game_id}", methods=["POST"])
@catcher
def events(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Retrieve events on a 110 game.
    '''
    identifier, game = parse_request(req)

    return func.HttpResponse(
        json.dumps(serialize.events(game.events, identifier)))


@app.function_name("game_info")
@app.route(route="info/{game_id}", methods=["POST"])
@catcher
def game_info(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Retrieve 110 game.
    '''
    identifier, game = parse_request(req)

    return func.HttpResponse(json.dumps(serialize.game(game, identifier)))


@app.function_name("invite_to_game")
@app.route(route="invite/{game_id}", methods=["POST"])
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


@app.function_name("join_game")
@app.route(route="join/{game_id}", methods=["POST"])
@catcher
def join_game(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Join a 110 game
    '''
    identifier, game = parse_request(req)
    game.join(identifier)
    game = GameService.save(game)

    return func.HttpResponse(json.dumps(serialize.game(game, identifier)))


@app.function_name("leave_game")
@app.route(route="leave/{game_id}", methods=["POST"])
@catcher
def leave_game(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Leave a 110 game
    '''
    identifier, game = parse_request(req)
    initial_event_knowledge = len(game.events)
    if isinstance(game.status, RoundStatus):
        game.automate(identifier)
    else:
        game.leave(identifier)
    game = GameService.save(game)

    return func.HttpResponse(
        json.dumps(serialize.game(game, identifier, initial_event_knowledge)))


@app.function_name("play")
@app.route(route="play/{game_id}", methods=["POST"])
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


@app.function_name("players")
@app.route(route="players/{game_id}", methods=["GET"])
@catcher
def players(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Retrieve players on a 110 game.
    '''
    _, game = parse_request(req)

    people_ids = list(map(lambda p: p.identifier, game.people))

    return func.HttpResponse(
        json.dumps(list(map(serialize.user, UserService.by_identifiers(people_ids)))))


@app.function_name("rescind_prepass")
@app.route(route="unpass/{game_id}", methods=["POST"])
@catcher
def rescind_prepass(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Unpass in a 110 game
    '''
    identifier, game = parse_request(req)
    initial_event_knowledge = len(game.events)

    game.act(Unpass(identifier))

    game = GameService.save(game)

    return func.HttpResponse(
        json.dumps(serialize.game(game, identifier, initial_event_knowledge)))


@app.function_name("search_games")
@app.route(route="games", methods=["GET"])
@catcher
def search_games(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Get games
    '''
    identifier, *_ = parse_request(req)

    body = req.get_json()
    max_count = body.get('max', 20)

    return func.HttpResponse(
        json.dumps(
            list(map(lambda g: serialize.game(g, identifier),
                     GameService.search(SearchGame(
                         name=body.get('searchText', ''),
                         client=identifier,
                         statuses=body.get('statuses', None),
                         active_player=body.get('activePlayer', None),
                         winner=body.get('winner', None)
                     ), max_count)))))


@app.function_name("search_users")
@app.route(route="users", methods=["GET"])
@catcher
def search_users(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Get users
    '''

    return func.HttpResponse(json.dumps(
        list(map(serialize.user, UserService.search(req.params.get('searchText', ''))))))


@app.function_name("select_trump")
@app.route(route="select/{game_id}", methods=["POST"])
@catcher
def select_trump(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Select trump in a 110 game
    '''
    identifier, game = parse_request(req)
    initial_event_knowledge = len(game.events)

    body = req.get_json()

    game.act(SelectTrump(identifier, SelectableSuit[body['suit']]))

    game = GameService.save(game)

    return func.HttpResponse(
        json.dumps(serialize.game(game, identifier, initial_event_knowledge)))


@app.function_name("self")
@app.route(route="self", methods=["PUT", "POST"])
@catcher
def update_self(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Create or update the user
    '''

    overwrite = req.method.upper() == 'PUT'

    identifier, *_ = parse_request(req)

    existing_user = UserService.by_identifier(identifier)
    provided_user = deserialize.user(req, req.get_json())

    save_user = provided_user if overwrite or not existing_user else existing_user

    return func.HttpResponse(json.dumps(
        serialize.user(UserService.save(save_user))))


@app.function_name("start_game")
@app.route(route="start/{game_id}", methods=["POST"])
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


@app.function_name("suggestion")
@app.route(route="suggestion/{game_id}", methods=["POST"])
@catcher
def suggestion(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Ask for a suggestion in a 110 game
    '''
    identifier, game = parse_request(req)

    return func.HttpResponse(
        json.dumps(serialize.suggestion(game.suggestion(), identifier)))
