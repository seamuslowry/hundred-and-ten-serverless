"""
The router for game operations.
"""

from typing import Optional

from beanie import PydanticObjectId
from fastapi import APIRouter

from src.mappers.client import deserialize, serialize
from src.models.client.requests import (
    ActRequest,
    GamePlayerKickRequest,
    GamePlayerLeaveRequest,
    GamePlayerRequest,
    SearchGamesRequest,
)
from src.models.client.responses import (
    Event,
    GameResponse,
    Player,
    UnorderedActionResponse,
)
from src.models.internal.errors import AuthorizationError, BadRequestError
from src.services import GameService, PlayerService

router = APIRouter(
    prefix="/players/{player_id}/games",
    tags=["Games"],
)


@router.get("/{game_id}", response_model=GameResponse)
async def game_info(player_id: str, game_id: PydanticObjectId):
    """Retrieve 110 game."""
    game = await GameService.get(game_id)

    return serialize.game(game, player_id)


@router.get("/{game_id}/spike", response_model=GameResponse)
async def spike_game_info(player_id: str, game_id: PydanticObjectId):
    """Retrieve 110 game with full round history (spike endpoint)."""
    game = await GameService.get(game_id)

    return serialize.game(game, player_id)


@router.post("/{game_id}/players", response_model=list[Event])
async def leave_game(
    player_id: str, game_id: PydanticObjectId, body: GamePlayerRequest
):
    """Leave a 110 game (automates the player)"""
    game = await GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    match body:
        case GamePlayerLeaveRequest():
            game.leave(player_id)
        case GamePlayerKickRequest():
            if player_id != game.organizer.id:
                raise AuthorizationError("Only the organizer may kick players")
            game.leave(body.player_id)
        case _:  # pragma: no cover
            # type: ignore[unreachable]
            raise BadRequestError(f"Invalid request {body}")

    game = await GameService.save(game)

    return serialize.events(game.events[initial_event_knowledge:], player_id)


@router.get("/{game_id}/players", response_model=list[Player])
async def game_players(game_id: PydanticObjectId):
    """Retrieve players in a 110 game."""
    game = await GameService.get(game_id)

    people_ids = [p.id for p in game.ordered_players]

    return [serialize.player(u) for u in await PlayerService.by_player_ids(people_ids)]


@router.post("/{game_id}/actions", response_model=list[Event])
async def act(player_id: str, game_id: PydanticObjectId, body: ActRequest):
    """Act in a 110 game"""
    game = await GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    game.act(deserialize.action(player_id, body))

    await GameService.save(game)

    return serialize.events(game.events[initial_event_knowledge:], player_id)


@router.post("/{game_id}/queued-actions", response_model=list[Event])
async def queued_action(player_id: str, game_id: PydanticObjectId, body: ActRequest):
    """Queue an action in a 110 game"""
    game = await GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    game.queue_action_for(player_id, deserialize.action(player_id, body))

    game = await GameService.save(game)

    return serialize.events(game.events[initial_event_knowledge:], player_id)


@router.delete("/{game_id}/queued-actions", response_model=list[Event])
async def remove_queued_action(player_id: str, game_id: PydanticObjectId):
    """Clear all queued actions for a player in a 110 game"""
    game = await GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    game.clear_queued_actions_for(player_id)

    await GameService.save(game)

    return serialize.events(game.events[initial_event_knowledge:], player_id)


@router.get("/{game_id}/events", response_model=list[Event])
async def events(
    player_id: str,
    game_id: PydanticObjectId,
    skip: int = 0,
    limit: Optional[int] = None,
):
    """Retrieve the events in a 110 game."""
    game = await GameService.get(game_id)

    return serialize.events(game.events, player_id)[
        skip : (skip + limit) if limit else None
    ]


@router.get("/{game_id}/suggestions", response_model=list[UnorderedActionResponse])
async def suggestion(player_id: str, game_id: PydanticObjectId):
    """Ask for suggestions in a 110 game"""
    game = await GameService.get(game_id)

    return [serialize.suggestion(s) for s in game.suggestions_for(player_id)]


@router.post("/search", response_model=list[GameResponse])
async def search_games(player_id: str, body: SearchGamesRequest):
    """Search for games"""
    return [
        serialize.game(g, player_id) for g in await GameService.search(player_id, body)
    ]
