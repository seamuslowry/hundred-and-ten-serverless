"""
The entrypoint for azure functions
"""

import json
import logging

import azure.functions as func

from utils.decorators import authenticate, catcher, get_identity
from utils.dtos.db import SearchGame, SearchLobby
from utils.mappers.client import deserialize, serialize
from utils.models import (
    Accessibility,
    Bid,
    BidAmount,
    Discard,
    HundredAndTenError,
    Lobby,
    Person,
    Play,
    SelectableSuit,
    SelectTrump,
    Unpass,
)
from utils.parsers import parse_game_request, parse_lobby_request
from utils.services import GameService, LobbyService, UserService

MIN_PLAYERS = 4

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


# =============================================================================
# Game endpoints (in-progress or completed games)
# =============================================================================


@app.function_name("bid")
@app.route(route="bid/{game_id}", methods=[func.HttpMethod.POST])
@catcher
@authenticate
def bid(req: func.HttpRequest) -> func.HttpResponse:
    """
    Bid in a 110 game
    """
    identifier, game = parse_game_request(req)
    initial_event_knowledge = len(game.events)

    body = req.get_json()

    game.act(Bid(identifier, BidAmount(body["amount"])))

    game = GameService.save(game)

    return func.HttpResponse(
        json.dumps(serialize.game(game, identifier, initial_event_knowledge))
    )


@app.function_name("discard")
@app.route(route="discard/{game_id}", methods=[func.HttpMethod.POST])
@catcher
@authenticate
def discard(req: func.HttpRequest) -> func.HttpResponse:
    """
    Discard in a 110 game
    """
    identifier, game = parse_game_request(req)
    initial_event_knowledge = len(game.events)

    body = req.get_json()

    game.act(Discard(identifier, [deserialize.card(c) for c in body.get("cards")]))

    game = GameService.save(game)

    return func.HttpResponse(
        json.dumps(serialize.game(game, identifier, initial_event_knowledge))
    )


@app.function_name("game_info")
@app.route(route="info/{game_id}", methods=[func.HttpMethod.GET])
@catcher
@authenticate
def game_info(req: func.HttpRequest) -> func.HttpResponse:
    """
    Retrieve 110 game.
    """
    identifier, game = parse_game_request(req)

    return func.HttpResponse(json.dumps(serialize.game(game, identifier)))


@app.function_name("game_players")
@app.route(route="players/game/{game_id}", methods=[func.HttpMethod.GET])
@catcher
@authenticate
def game_players(req: func.HttpRequest) -> func.HttpResponse:
    """
    Retrieve players in a 110 game.
    """
    _, game = parse_game_request(req)

    people_ids = [p.identifier for p in game.ordered_players]

    return func.HttpResponse(
        json.dumps(list(map(serialize.user, UserService.by_identifiers(people_ids))))
    )


@app.function_name("leave_game")
@app.route(route="leave/game/{game_id}", methods=[func.HttpMethod.POST])
@catcher
@authenticate
def leave_game(req: func.HttpRequest) -> func.HttpResponse:
    """
    Leave a 110 game (automates the player)
    """
    identifier, game = parse_game_request(req)
    initial_event_knowledge = len(game.events)

    game.leave(identifier)
    game = GameService.save(game)

    return func.HttpResponse(
        json.dumps(serialize.game(game, identifier, initial_event_knowledge))
    )


@app.function_name("play")
@app.route(route="play/{game_id}", methods=[func.HttpMethod.POST])
@catcher
@authenticate
def play(req: func.HttpRequest) -> func.HttpResponse:
    """
    Play a card in a 110 game
    """
    identifier, game = parse_game_request(req)
    initial_event_knowledge = len(game.events)

    body = req.get_json()

    game.act(Play(identifier, deserialize.card(body.get("card"))))

    game = GameService.save(game)

    return func.HttpResponse(
        json.dumps(serialize.game(game, identifier, initial_event_knowledge))
    )


@app.function_name("rescind_prepass")
@app.route(route="unpass/{game_id}", methods=[func.HttpMethod.POST])
@catcher
@authenticate
def rescind_prepass(req: func.HttpRequest) -> func.HttpResponse:
    """
    Unpass in a 110 game
    """
    identifier, game = parse_game_request(req)
    initial_event_knowledge = len(game.events)

    game.act(Unpass(identifier))

    game = GameService.save(game)

    return func.HttpResponse(
        json.dumps(serialize.game(game, identifier, initial_event_knowledge))
    )


@app.function_name("search_games")
@app.route(route="games", methods=[func.HttpMethod.POST])
@catcher
@authenticate
def search_games(req: func.HttpRequest) -> func.HttpResponse:
    """
    Search for games
    """
    identifier = get_identity().id

    body = req.get_json()
    max_count = body.get("max", 20)

    return func.HttpResponse(
        json.dumps(
            list(
                map(
                    lambda g: serialize.game(g, identifier),
                    GameService.search(
                        SearchGame(
                            name=body.get("searchText", ""),
                            client=identifier,
                            statuses=body.get("statuses", None),
                            active_player=body.get("activePlayer", None),
                            winner=body.get("winner", None),
                        ),
                        max_count,
                    ),
                )
            )
        )
    )


@app.function_name("select_trump")
@app.route(route="select/{game_id}", methods=[func.HttpMethod.POST])
@catcher
@authenticate
def select_trump(req: func.HttpRequest) -> func.HttpResponse:
    """
    Select trump in a 110 game
    """
    identifier, game = parse_game_request(req)
    initial_event_knowledge = len(game.events)

    body = req.get_json()

    game.act(SelectTrump(identifier, SelectableSuit[body["suit"]]))

    game = GameService.save(game)

    return func.HttpResponse(
        json.dumps(serialize.game(game, identifier, initial_event_knowledge))
    )


@app.function_name("suggestion")
@app.route(route="suggestion/{game_id}", methods=[func.HttpMethod.GET])
@catcher
@authenticate
def suggestion(req: func.HttpRequest) -> func.HttpResponse:
    """
    Ask for a suggestion in a 110 game
    """
    identifier, game = parse_game_request(req)

    return func.HttpResponse(
        json.dumps(serialize.suggestion(game.suggestion(), identifier))
    )


# =============================================================================
# Lobby endpoints (waiting for players)
# =============================================================================


@app.function_name("create_lobby")
@app.route(route="create", methods=[func.HttpMethod.POST])
@catcher
@authenticate
def create_lobby(req: func.HttpRequest) -> func.HttpResponse:
    """
    Create a new 110 lobby.
    """
    logging.info("Initiating create lobby request.")

    identifier = get_identity().id

    logging.debug("Creating lobby for %s", identifier)

    body = req.get_json()

    lobby = Lobby(
        organizer=Person(identifier=identifier),
        name=body.get("name", f"{identifier} Game"),
        accessibility=Accessibility[
            body.get("accessibility", Accessibility.PUBLIC.name)
        ],
    )

    lobby = LobbyService.save(lobby)

    logging.debug("Lobby %s created successfully", lobby.seed)

    return func.HttpResponse(json.dumps(serialize.lobby(lobby)))


@app.function_name("invite_to_lobby")
@app.route(route="invite/{lobby_id}", methods=[func.HttpMethod.POST])
@catcher
@authenticate
def invite_to_lobby(req: func.HttpRequest) -> func.HttpResponse:
    """
    Invite to join a 110 lobby
    """
    identifier, lobby = parse_lobby_request(req)

    body = req.get_json()
    invitees: list[str] = body.get("invitees", [])

    for invitee in invitees:
        lobby.invite(identifier, Person(identifier=invitee))
    lobby = LobbyService.save(lobby)

    return func.HttpResponse(json.dumps(serialize.lobby(lobby)))


@app.function_name("join_lobby")
@app.route(route="join/{lobby_id}", methods=[func.HttpMethod.POST])
@catcher
@authenticate
def join_lobby(req: func.HttpRequest) -> func.HttpResponse:
    """
    Join a 110 lobby
    """
    identifier, lobby = parse_lobby_request(req)
    lobby.join(Person(identifier))
    lobby = LobbyService.save(lobby)

    return func.HttpResponse(json.dumps(serialize.lobby(lobby)))


@app.function_name("leave_lobby")
@app.route(route="leave/lobby/{lobby_id}", methods=[func.HttpMethod.POST])
@catcher
@authenticate
def leave_lobby(req: func.HttpRequest) -> func.HttpResponse:
    """
    Leave a 110 lobby
    """
    identifier, lobby = parse_lobby_request(req)
    lobby.leave(identifier)
    lobby = LobbyService.save(lobby)

    return func.HttpResponse(json.dumps(serialize.lobby(lobby)))


@app.function_name("lobby_info")
@app.route(route="lobby/{lobby_id}", methods=[func.HttpMethod.GET])
@catcher
@authenticate
def lobby_info(req: func.HttpRequest) -> func.HttpResponse:
    """
    Retrieve 110 lobby.
    """
    _, lobby = parse_lobby_request(req)

    return func.HttpResponse(json.dumps(serialize.lobby(lobby)))


@app.function_name("lobby_players")
@app.route(route="players/lobby/{lobby_id}", methods=[func.HttpMethod.GET])
@catcher
@authenticate
def lobby_players(req: func.HttpRequest) -> func.HttpResponse:
    """
    Retrieve players in a 110 lobby.
    """
    _, lobby = parse_lobby_request(req)

    people_ids = [p.identifier for p in lobby.ordered_players]

    return func.HttpResponse(
        json.dumps(list(map(serialize.user, UserService.by_identifiers(people_ids))))
    )


@app.function_name("search_lobbies")
@app.route(route="lobbies", methods=[func.HttpMethod.POST])
@catcher
@authenticate
def search_lobbies(req: func.HttpRequest) -> func.HttpResponse:
    """
    Search for lobbies
    """
    identifier = get_identity().id

    body = req.get_json()
    max_count = body.get("max", 20)

    return func.HttpResponse(
        json.dumps(
            list(
                map(
                    serialize.lobby,
                    LobbyService.search(
                        SearchLobby(
                            name=body.get("searchText", ""),
                            client=identifier,
                        ),
                        max_count,
                    ),
                )
            )
        )
    )


@app.function_name("start_game")
@app.route(route="start/{lobby_id}", methods=[func.HttpMethod.POST])
@catcher
@authenticate
def start_game(req: func.HttpRequest) -> func.HttpResponse:
    """
    Start a 110 game from a lobby
    """
    identifier, lobby = parse_lobby_request(req)

    if identifier != lobby.organizer.identifier:
        raise HundredAndTenError("Only the organizer can start the game")

    # Add CPU players if needed
    for num in range(len(lobby.ordered_players), MIN_PLAYERS):
        cpu_identifier = str(num + 1)
        lobby.invite(identifier, Person(cpu_identifier, automate=True))
        lobby.join(Person(cpu_identifier, automate=True))

    # Start the game (converts lobby record to game record)
    game = LobbyService.start_game(lobby)

    return func.HttpResponse(json.dumps(serialize.game(game, identifier, 0)))


# =============================================================================
# User endpoints
# =============================================================================


@app.function_name("search_users")
@app.route(route="users", methods=[func.HttpMethod.GET])
@catcher
@authenticate
def search_users(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get users
    """

    return func.HttpResponse(
        json.dumps(
            list(
                map(
                    serialize.user, UserService.search(req.params.get("searchText", ""))
                )
            )
        )
    )


@app.function_name("self")
@app.route(route="self", methods=[func.HttpMethod.PUT, func.HttpMethod.POST])
@catcher
@authenticate
def update_self(req: func.HttpRequest) -> func.HttpResponse:
    """
    Create or update the user
    """

    overwrite = req.method.upper() == "PUT"

    identifier = get_identity().id

    existing_user = UserService.by_identifier(identifier)
    provided_user = deserialize.user(req.get_json())

    save_user = provided_user if overwrite or not existing_user else existing_user

    return func.HttpResponse(json.dumps(serialize.user(UserService.save(save_user))))
