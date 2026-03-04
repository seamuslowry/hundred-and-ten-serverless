"""
The router for game operations.
"""

from typing import Union

from fastapi import APIRouter, Depends

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

router = APIRouter(prefix="/games", tags=["Games"])


@router.get("/{game_id}", response_model=GameResponse)
def game_info(game_id: str, identity: Identity = Depends(get_identity)):
    """Retrieve 110 game."""
    game = GameService.get(game_id)

    return serialize.game(game, identity.id)


@router.get("/{game_id}/players", response_model=list[User])
def game_players(game_id: str):
    """Retrieve players in a 110 game."""
    game = GameService.get(game_id)

    people_ids = [p.identifier for p in game.ordered_players]

    return [serialize.user(u) for u in UserService.by_identifiers(people_ids)]


@router.post("/search", response_model=list[GameResponse])
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


@router.get("/{game_id}/suggestion", response_model=SuggestionResponse)
def suggestion(game_id: str, identity: Identity = Depends(get_identity)):
    """Ask for a suggestion in a 110 game"""
    game = GameService.get(game_id)

    return serialize.suggestion(game.suggestion(), identity.id)


@router.post("/{game_id}/bid", response_model=GameResponse)
def bid(game_id: str, body: BidRequest, identity: Identity = Depends(get_identity)):
    """Bid in a 110 game"""
    game = GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    game.act(Bid(identity.id, BidAmount(body.amount)))

    game = GameService.save(game)

    return serialize.game(game, identity.id, initial_event_knowledge)


@router.post("/{game_id}/unpass", response_model=GameResponse)
def rescind_prepass(game_id: str, identity: Identity = Depends(get_identity)):
    """Unpass in a 110 game"""
    game = GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    game.act(Unpass(identity.id))

    game = GameService.save(game)

    return serialize.game(game, identity.id, initial_event_knowledge)


@router.post("/{game_id}/select", response_model=GameResponse)
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


@router.post("/{game_id}/discard", response_model=GameResponse)
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


@router.post("/{game_id}/play", response_model=GameResponse)
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


@router.post("/{game_id}/leave", response_model=GameResponse)
def leave_game(game_id: str, identity: Identity = Depends(get_identity)):
    """Leave a 110 game (automates the player)"""
    game = GameService.get(game_id)
    initial_event_knowledge = len(game.events)

    game.leave(identity.id)
    game = GameService.save(game)

    return serialize.game(game, identity.id, initial_event_knowledge)
