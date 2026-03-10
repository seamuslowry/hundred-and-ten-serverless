"""Game Service unit tests"""

import pytest
from bson import ObjectId

from src.main.models.client.requests import SearchGamesRequest
from src.main.models.internal import Game, Human, Lobby, PersonGroup
from src.main.services import GameService, LobbyService


async def _make_game(name: str = "") -> Game:
    """Create a valid Game from a saved Lobby with players"""
    lobby = await LobbyService.save(
        Lobby(
            name=name,
            organizer=Human("p1"),
            players=PersonGroup(
                [
                    Human(identifier="p2"),
                ]
            ),
        )
    )
    return Game.from_lobby(lobby)


async def test_save_game():
    """Game can be saved to the DB"""
    game = await _make_game()

    assert await GameService.save(game) is not None


async def test_get_game():
    """Game can be retrieved from the DB"""
    original_game = await _make_game()
    saved_game = await GameService.save(original_game)
    assert saved_game.id
    game = await GameService.get(saved_game.id)

    assert game is not None
    assert game.id == saved_game.id


async def test_get_non_existent_game():
    """Unknown game cannot be retrieved from the DB"""
    with pytest.raises(ValueError):
        await GameService.get(str(ObjectId()))


async def test_search_game():
    """Games can be searched in the DB"""
    text = f"search_test{ObjectId()}"
    games = []
    for i in range(5):
        game = await _make_game(name=f"{text} {i}")
        games.append(await GameService.save(game))

    found_games = await GameService.search(
        "p1",
        SearchGamesRequest(
            search_text=text,
            statuses=None,
            active_player=None,
            winner=None,
            limit=len(games) + 1,
        ),
    )

    assert len(found_games) == len(games)


async def test_search_game_with_filters():
    """Search with optional filters exercises all code paths"""
    text = f"filter_test{ObjectId()}"
    games = []

    # Create 3 games with different properties
    for i in range(3):
        game = await _make_game(name=f"{text} {i}")
        games.append(await GameService.save(game))

    # Get the active player from the first game
    game_with_player = games[0]
    active_player_id = game_with_player.active_round.active_player.identifier

    # Search with activePlayer filter (exercises line 42)
    found_with_player = await GameService.search(
        "p1",
        SearchGamesRequest(
            search_text=text,
            active_player=active_player_id,
            winner=None,
            statuses=None,
            limit=10,
        ),
    )
    assert len(found_with_player) > 0

    # Search with winner filter (exercises line 44 - already covered but verify)
    found_with_winner = await GameService.search(
        "p1",
        SearchGamesRequest(
            search_text=text,
            active_player=None,
            winner="nonexistent_winner",
            statuses=None,
            limit=10,
        ),
    )
    assert len(found_with_winner) == 0

    # Search with statuses filter (exercises line 46)
    found_with_status = await GameService.search(
        "p1",
        SearchGamesRequest(
            search_text=text,
            active_player=None,
            winner=None,
            statuses=[games[0].status.name],
            limit=10,
        ),
    )
    assert len(found_with_status) > 0
