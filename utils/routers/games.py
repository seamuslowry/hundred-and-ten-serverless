"""
The router for game operations.
"""

from typing import Union

from fastapi import APIRouter

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
from utils.mappers.client import deserialize, serialize
from utils.models import (
    Bid,
    BidAmount,
    Discard,
    Play,
    SelectableSuit,
    SelectTrump,
    Unpass,
)
from utils.services import GameService, UserService

# Type alias for game responses (can be started or completed)
GameResponse = Union[StartedGame, CompletedGame]

router = APIRouter(
    prefix="/players/{player_id}/games",
    tags=["Games"],
)


@router.get("/{game_id}", response_model=GameResponse)
def game_info(player_id: str, game_id: str):
    """Retrieve 110 game."""
    game = GameService.get(game_id)

    return serialize.game(game, player_id)


@router.get("/{game_id}/players", response_model=list[User])
def game_players(game_id: str):
    """Retrieve players in a 110 game."""
    game = GameService.get(game_id)

    people_ids = [p.identifier for p in game.ordered_players]

    return [serialize.user(u) for u in UserService.by_identifiers(people_ids)]


@router.post("/search", response_model=list[GameResponse])
def search_games(player_id: str, body: SearchGamesRequest):
    """Search for games"""
    return [
        serialize.game(g, player_id)
        for g in GameService.search(
            SearchGame(
                name=body.searchText,
                client=player_id,
                statuses=body.statuses,
                active_player=body.activePlayer,
                winner=body.winner,
            ),
            body.max,
        )
    ]


@router.get("/{game_id}/suggestion", response_model=SuggestionResponse)
def suggestion(player_id: str, game_id: str):
    """Ask for a suggestion in a 110 game"""
    game = GameService.get(game_id)

    return serialize.suggestion(game.suggestion(), player_id)


@router.post("/{game_id}/bid", response_model=GameResponse)
def bid(player_id: str, game_id: str, body: BidRequest):
    """Bid in a 110 game"""
    game = GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    game.act(Bid(player_id, BidAmount(body.amount)))

    game = GameService.save(game)

    return serialize.game(game, player_id, initial_event_knowledge)


@router.post("/{game_id}/unpass", response_model=GameResponse)
def rescind_prepass(player_id: str, game_id: str):
    """Unpass in a 110 game"""
    game = GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    game.act(Unpass(player_id))

    game = GameService.save(game)

    return serialize.game(game, player_id, initial_event_knowledge)


@router.post("/{game_id}/select", response_model=GameResponse)
def select_trump(
    player_id: str,
    game_id: str,
    body: SelectTrumpRequest,
):
    """Select trump in a 110 game"""
    game = GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    game.act(SelectTrump(player_id, SelectableSuit[body.suit.value]))

    game = GameService.save(game)

    return serialize.game(game, player_id, initial_event_knowledge)


@router.post("/{game_id}/discard", response_model=GameResponse)
def discard(player_id: str, game_id: str, body: DiscardRequest):
    """Discard in a 110 game"""
    game = GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    game.act(
        Discard(
            player_id,
            [deserialize.card(c) for c in body.cards],
        )
    )

    game = GameService.save(game)

    return serialize.game(game, player_id, initial_event_knowledge)


@router.post("/{game_id}/play", response_model=GameResponse)
def play(player_id: str, game_id: str, body: PlayRequest):
    """Play a card in a 110 game"""
    game = GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    game.act(
        Play(
            player_id,
            deserialize.card(body.card),
        )
    )

    game = GameService.save(game)

    return serialize.game(game, player_id, initial_event_knowledge)


@router.post("/{game_id}/leave", response_model=GameResponse)
def leave_game(player_id: str, game_id: str):
    """Leave a 110 game (automates the player)"""
    game = GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    game.leave(player_id)
    game = GameService.save(game)

    return serialize.game(game, player_id, initial_event_knowledge)
