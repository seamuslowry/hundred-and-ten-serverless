"""Game Service unit tests"""

from unittest import TestCase

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


class TestGameService(TestCase):
    """Unit tests to ensure game service works as expected"""

    async def test_save_game(self):
        """Game can be saved to the DB"""
        game = await _make_game()

        self.assertIsNotNone(GameService.save(game))

    async def test_get_game(self):
        """Game can be retrieved from the DB"""
        original_game = await _make_game()
        await GameService.save(original_game)
        assert original_game.id
        game = await GameService.get(original_game.id)

        self.assertIsNotNone(game)
        self.assertEqual(game.id, original_game.id)

    def test_get_non_existent_game(self):
        """Unknown game cannot be retrieved from the DB"""
        self.assertRaises(ValueError, GameService.get, str(ObjectId()))

    async def test_search_game(self):
        """Games can be searched in the DB"""
        text = f"search_test{ObjectId()}"
        games = [
            GameService.save(await _make_game(name=f"{text} {i}")) for i in range(5)
        ]

        found_games = await GameService.search(
            "p1",
            SearchGamesRequest(
                searchText=text,
                statuses=None,
                activePlayer=None,
                winner=None,
                limit=len(games) + 1,
            ),
        )

        self.assertEqual(len(found_games), len(games))
