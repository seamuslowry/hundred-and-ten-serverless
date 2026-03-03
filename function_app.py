"""
The entrypoint for azure functions, wrapping a FastAPI app via AsgiFunctionApp
"""

from typing import Union

import azure.functions as func
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from utils.auth import Identity, get_identity
from utils.dtos.db import SearchGame
from utils.dtos.requests import (
    BidRequest,
    DiscardRequest,
    PlayRequest,
    SearchGamesRequest,
    SelectTrumpRequest,
)
from utils.dtos.responses import (
    CompletedGame,
    StartedGame,
    SuggestionResponse,
    User,
)
from utils.errors import AuthenticationError, AuthorizationError
from utils.mappers.client import deserialize, serialize
from utils.models import (
    Bid,
    BidAmount,
    Discard,
    HundredAndTenError,
    Play,
    SelectableSuit,
    SelectTrump,
    Unpass,
)
from utils.routers import lobbies, users
from utils.services import GameService, UserService

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

fastapi_app.include_router(lobbies)

# =============================================================================
# User endpoints
# =============================================================================

fastapi_app.include_router(users)

# =============================================================================
# Azure Functions ASGI wrapper
# =============================================================================

app = func.AsgiFunctionApp(app=fastapi_app, http_auth_level=func.AuthLevel.ANONYMOUS)
