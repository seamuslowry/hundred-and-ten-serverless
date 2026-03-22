"""
The router for game operations.
"""

from typing import Union

from beanie import PydanticObjectId
from fastapi import APIRouter

from src.main.mappers.client import deserialize, serialize
from src.main.models.client.requests import (
    ActRequest,
    SearchGamesRequest,
)
from src.main.models.client.responses import (
    CompletedGame,
    Event,
    Player,
    StartedGame,
    SuggestionResponse,
)
from src.main.models.internal import (
    NaiveAutomatedPlayer,
)
from src.main.services import GameService, PlayerService

# Type alias for game responses (can be started or completed)
GameResponse = Union[StartedGame, CompletedGame]

router = APIRouter(
    prefix="/players/{player_id}/games",
    tags=["Games"],
)


@router.get("/{game_id}", response_model=GameResponse)
async def game_info(player_id: str, game_id: PydanticObjectId):
    """Retrieve 110 game."""
    game = await GameService.get(game_id)

    return serialize.game(game, player_id)


@router.get("/{game_id}/players", response_model=list[Player])
async def game_players(game_id: PydanticObjectId):
    """Retrieve players in a 110 game."""
    game = await GameService.get(game_id)

    people_ids = [p.id for p in game.ordered_players]

    return [serialize.player(u) for u in await PlayerService.by_player_ids(people_ids)]


@router.post("", response_model=list[GameResponse])
async def search_games(player_id: str, body: SearchGamesRequest):
    """Search for games"""
    return [
        serialize.game(g, player_id) for g in await GameService.search(player_id, body)
    ]


@router.get("/{game_id}/suggestion", response_model=SuggestionResponse)
async def suggestion(player_id: str, game_id: PydanticObjectId):
    """Ask for a suggestion in a 110 game"""
    game = await GameService.get(game_id)

    return serialize.action(
        NaiveAutomatedPlayer(player_id).act(game.game_state_for(player_id))
    )


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

    await GameService.save(game)

    return serialize.events(game.events[initial_event_knowledge:], player_id)


@router.delete("/{game_id}/queued-actions", response_model=list[Event])
async def remove_queued_action(player_id: str, game_id: PydanticObjectId):
    """Clear all queued actions for a player in a 110 game"""
    game = await GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    game.clear_queued_actions_for(player_id)

    await GameService.save(game)

    return serialize.events(game.events[initial_event_knowledge:], player_id)


@router.post("/{game_id}/leave", response_model=list[Event])
async def leave_game(player_id: str, game_id: PydanticObjectId):
    """Leave a 110 game (automates the player)"""
    game = await GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    game.leave(player_id)
    game = await GameService.save(game)

    return serialize.events(game.events[initial_event_knowledge:], player_id)
