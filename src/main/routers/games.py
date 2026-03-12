"""
The router for game operations.
"""

from typing import Union

from beanie import PydanticObjectId
from fastapi import APIRouter

from src.main.mappers.client import deserialize, serialize
from src.main.models.client.requests import (
    BidRequest,
    DiscardRequest,
    PlayRequest,
    SearchGamesRequest,
    SelectTrumpRequest,
)
from src.main.models.client.responses import (
    CompletedGame,
    StartedGame,
    SuggestionResponse,
    User,
)
from src.main.models.internal import (
    Bid,
    BidAmount,
    Discard,
    NaiveAutomatedPlayer,
    Play,
    SelectableSuit,
    SelectTrump,
    Unpass,
)
from src.main.services import GameService, UserService

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


@router.get("/{game_id}/players", response_model=list[User])
async def game_players(game_id: PydanticObjectId):
    """Retrieve players in a 110 game."""
    game = await GameService.get(game_id)

    people_ids = [p.identifier for p in game.ordered_players]

    return [serialize.user(u) for u in await UserService.by_identifiers(people_ids)]


@router.post("/search", response_model=list[GameResponse])
async def search_games(player_id: str, body: SearchGamesRequest):
    """Search for games"""
    return [
        serialize.game(g, player_id) for g in await GameService.search(player_id, body)
    ]


@router.get("/{game_id}/suggestion", response_model=SuggestionResponse)
async def suggestion(player_id: str, game_id: PydanticObjectId):
    """Ask for a suggestion in a 110 game"""
    game = await GameService.get(game_id)

    return serialize.suggestion(
        NaiveAutomatedPlayer(player_id).act(game.game_state_for(player_id))
    )


@router.post("/{game_id}/bid", response_model=GameResponse)
async def bid(player_id: str, game_id: PydanticObjectId, body: BidRequest):
    """Bid in a 110 game"""
    game = await GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    game.act(Bid(player_id, BidAmount(body.amount)))

    await GameService.save(game)

    return serialize.game(game, player_id, initial_event_knowledge)


@router.post("/{game_id}/unpass", response_model=GameResponse)
async def rescind_prepass(player_id: str, game_id: PydanticObjectId):
    """Unpass in a 110 game"""
    game = await GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    game.act(Unpass(player_id))

    await GameService.save(game)

    return serialize.game(game, player_id, initial_event_knowledge)


@router.post("/{game_id}/select", response_model=GameResponse)
async def select_trump(
    player_id: str,
    game_id: PydanticObjectId,
    body: SelectTrumpRequest,
):
    """Select trump in a 110 game"""
    game = await GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    game.act(SelectTrump(player_id, SelectableSuit[body.suit.value]))

    game = await GameService.save(game)

    return serialize.game(game, player_id, initial_event_knowledge)


@router.post("/{game_id}/discard", response_model=GameResponse)
async def discard(player_id: str, game_id: PydanticObjectId, body: DiscardRequest):
    """Discard in a 110 game"""
    game = await GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    game.act(
        Discard(
            player_id,
            [deserialize.card(c) for c in body.cards],
        )
    )

    game = await GameService.save(game)

    return serialize.game(game, player_id, initial_event_knowledge)


@router.post("/{game_id}/play", response_model=GameResponse)
async def play(player_id: str, game_id: PydanticObjectId, body: PlayRequest):
    """Play a card in a 110 game"""
    game = await GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    game.act(
        Play(
            player_id,
            deserialize.card(body.card),
        )
    )

    game = await GameService.save(game)

    return serialize.game(game, player_id, initial_event_knowledge)


@router.post("/{game_id}/leave", response_model=GameResponse)
async def leave_game(player_id: str, game_id: PydanticObjectId):
    """Leave a 110 game (automates the player)"""
    game = await GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    game.leave(player_id)
    game = await GameService.save(game)

    return serialize.game(game, player_id, initial_event_knowledge)
