"""
The entrypoint for azure functions, wrapping a FastAPI app via AsgiFunctionApp
"""

import logging
from typing import Union

import azure.functions as func
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from utils.auth import Identity, get_identity
from utils.dtos.db import SearchGame, SearchLobby
from utils.dtos.requests import (
    BidRequest,
    CreateLobbyRequest,
    DiscardRequest,
    InviteRequest,
    PlayRequest,
    SearchGamesRequest,
    SearchLobbiesRequest,
    SelectTrumpRequest,
)
from utils.dtos.responses import (
    CompletedGame,
    StartedGame,
    SuggestionResponse,
    User,
    WaitingGame,
)
from utils.errors import AuthenticationError, AuthorizationError
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
from utils.routers import users
from utils.services import GameService, LobbyService, UserService

MIN_PLAYERS = 4

fastapi_app = FastAPI()

# Type alias for game responses (can be started or completed)
GameResponse = Union[StartedGame, CompletedGame]


# =============================================================================
# Exception handlers
# =============================================================================


@fastapi_app.exception_handler(AuthenticationError)
def authentication_error_handler(_: Request, exc: AuthenticationError) -> JSONResponse:
    """Return 401 for authentication errors"""
    return JSONResponse(status_code=401, content=str(exc))


@fastapi_app.exception_handler(AuthorizationError)
def authorization_error_handler(_: Request, exc: AuthorizationError) -> JSONResponse:
    """Return 403 for authorization errors"""
    return JSONResponse(status_code=403, content=str(exc))


@fastapi_app.exception_handler(HundredAndTenError)
def game_error_handler(_: Request, exc: HundredAndTenError) -> JSONResponse:
    """Return 400 for game errors"""
    return JSONResponse(status_code=400, content=str(exc))


@fastapi_app.exception_handler(ValueError)
def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    """Return 400 for value errors"""
    return JSONResponse(status_code=400, content=str(exc))


# =============================================================================
# Game endpoints (in-progress or completed games)
# =============================================================================


@fastapi_app.post("/bid/{game_id}", response_model=GameResponse)
def bid(game_id: str, body: BidRequest, identity: Identity = Depends(get_identity)):
    """Bid in a 110 game"""
    game = GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    game.act(Bid(identity.id, BidAmount(body.amount)))

    game = GameService.save(game)

    return serialize.game(game, identity.id, initial_event_knowledge)


@fastapi_app.post("/discard/{game_id}", response_model=GameResponse)
def discard(
    game_id: str, body: DiscardRequest, identity: Identity = Depends(get_identity)
):
    """Discard in a 110 game"""
    game = GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    game.act(
        Discard(
            identity.id,
            [deserialize.card(c) for c in body.cards],
        )
    )

    game = GameService.save(game)

    return serialize.game(game, identity.id, initial_event_knowledge)


@fastapi_app.get("/info/{game_id}", response_model=GameResponse)
def game_info(game_id: str, identity: Identity = Depends(get_identity)):
    """Retrieve 110 game."""
    game = GameService.get(game_id)

    return serialize.game(game, identity.id)


@fastapi_app.get("/players/game/{game_id}", response_model=list[User])
def game_players(game_id: str, _identity: Identity = Depends(get_identity)):
    """Retrieve players in a 110 game."""
    game = GameService.get(game_id)

    people_ids = [p.identifier for p in game.ordered_players]

    return [serialize.user(u) for u in UserService.by_identifiers(people_ids)]


@fastapi_app.post("/leave/game/{game_id}", response_model=GameResponse)
def leave_game(game_id: str, identity: Identity = Depends(get_identity)):
    """Leave a 110 game (automates the player)"""
    game = GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    game.leave(identity.id)
    game = GameService.save(game)

    return serialize.game(game, identity.id, initial_event_knowledge)


@fastapi_app.post("/play/{game_id}", response_model=GameResponse)
def play(game_id: str, body: PlayRequest, identity: Identity = Depends(get_identity)):
    """Play a card in a 110 game"""
    game = GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    game.act(
        Play(
            identity.id,
            deserialize.card(body.card),
        )
    )

    game = GameService.save(game)

    return serialize.game(game, identity.id, initial_event_knowledge)


@fastapi_app.post("/unpass/{game_id}", response_model=GameResponse)
def rescind_prepass(game_id: str, identity: Identity = Depends(get_identity)):
    """Unpass in a 110 game"""
    game = GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    game.act(Unpass(identity.id))

    game = GameService.save(game)

    return serialize.game(game, identity.id, initial_event_knowledge)


@fastapi_app.post("/games", response_model=list[GameResponse])
def search_games(body: SearchGamesRequest, identity: Identity = Depends(get_identity)):
    """Search for games"""
    return [
        serialize.game(g, identity.id)
        for g in GameService.search(
            SearchGame(
                name=body.searchText,
                client=identity.id,
                statuses=body.statuses,
                active_player=body.activePlayer,
                winner=body.winner,
            ),
            body.max,
        )
    ]


@fastapi_app.post("/select/{game_id}", response_model=GameResponse)
def select_trump(
    game_id: str,
    body: SelectTrumpRequest,
    identity: Identity = Depends(get_identity),
):
    """Select trump in a 110 game"""
    game = GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    game.act(SelectTrump(identity.id, SelectableSuit[body.suit.value]))

    game = GameService.save(game)

    return serialize.game(game, identity.id, initial_event_knowledge)


@fastapi_app.get("/suggestion/{game_id}", response_model=SuggestionResponse)
def suggestion(game_id: str, identity: Identity = Depends(get_identity)):
    """Ask for a suggestion in a 110 game"""
    game = GameService.get(game_id)

    return serialize.suggestion(game.suggestion(), identity.id)


# =============================================================================
# Lobby endpoints (waiting for players)
# =============================================================================


@fastapi_app.post("/create", response_model=WaitingGame)
def create_lobby(body: CreateLobbyRequest, identity: Identity = Depends(get_identity)):
    """Create a new 110 lobby."""
    logging.info("Initiating create lobby request.")

    logging.debug("Creating lobby for %s", identity.id)

    lobby = Lobby(
        organizer=Person(identifier=identity.id),
        name=body.name,
        accessibility=Accessibility[body.accessibility],
    )

    lobby = LobbyService.save(lobby)

    logging.debug("Lobby %s created successfully", lobby.seed)

    return serialize.lobby(lobby)


@fastapi_app.post("/invite/{lobby_id}", response_model=WaitingGame)
def invite_to_lobby(
    lobby_id: str, body: InviteRequest, identity: Identity = Depends(get_identity)
):
    """Invite to join a 110 lobby"""
    lobby = LobbyService.get(lobby_id)

    for invitee in body.invitees:
        lobby.invite(identity.id, Person(identifier=invitee))
    lobby = LobbyService.save(lobby)

    return serialize.lobby(lobby)


@fastapi_app.post("/join/{lobby_id}", response_model=WaitingGame)
def join_lobby(lobby_id: str, identity: Identity = Depends(get_identity)):
    """Join a 110 lobby"""
    lobby = LobbyService.get(lobby_id)
    lobby.join(Person(identity.id))
    lobby = LobbyService.save(lobby)

    return serialize.lobby(lobby)


@fastapi_app.post("/leave/lobby/{lobby_id}", response_model=WaitingGame)
def leave_lobby(lobby_id: str, identity: Identity = Depends(get_identity)):
    """Leave a 110 lobby"""
    lobby = LobbyService.get(lobby_id)
    lobby.leave(identity.id)
    lobby = LobbyService.save(lobby)

    return serialize.lobby(lobby)


@fastapi_app.get("/lobby/{lobby_id}", response_model=WaitingGame)
def lobby_info(lobby_id: str, _identity: Identity = Depends(get_identity)):
    """Retrieve 110 lobby."""
    lobby = LobbyService.get(lobby_id)

    return serialize.lobby(lobby)


@fastapi_app.get("/players/lobby/{lobby_id}", response_model=list[User])
def lobby_players(lobby_id: str, _identity: Identity = Depends(get_identity)):
    """Retrieve players in a 110 lobby."""
    lobby = LobbyService.get(lobby_id)

    people_ids = [p.identifier for p in lobby.ordered_players]

    return [serialize.user(u) for u in UserService.by_identifiers(people_ids)]


@fastapi_app.post("/lobbies", response_model=list[WaitingGame])
def search_lobbies(
    body: SearchLobbiesRequest, identity: Identity = Depends(get_identity)
):
    """Search for lobbies"""
    return [
        serialize.lobby(lobby)
        for lobby in LobbyService.search(
            SearchLobby(
                name=body.searchText,
                client=identity.id,
            ),
            body.max,
        )
    ]


@fastapi_app.post("/start/{lobby_id}", response_model=StartedGame)
def start_game(lobby_id: str, identity: Identity = Depends(get_identity)):
    """Start a 110 game from a lobby"""
    lobby = LobbyService.get(lobby_id)

    if identity.id != lobby.organizer.identifier:
        raise HundredAndTenError("Only the organizer can start the game")

    # Add CPU players if needed
    for num in range(len(lobby.ordered_players), MIN_PLAYERS):
        cpu_identifier = str(num + 1)
        lobby.invite(identity.id, Person(cpu_identifier, automate=True))
        lobby.join(Person(cpu_identifier, automate=True))

    # Start the game (converts lobby record to game record)
    game = LobbyService.start_game(lobby)

    return serialize.game(game, identity.id, 0)


# =============================================================================
# User endpoints
# =============================================================================

fastapi_app.include_router(users)

# =============================================================================
# Azure Functions ASGI wrapper
# =============================================================================

app = func.AsgiFunctionApp(app=fastapi_app, http_auth_level=func.AuthLevel.ANONYMOUS)
