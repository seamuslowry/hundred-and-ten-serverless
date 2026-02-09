"""Game Service unit tests"""

from unittest import TestCase

from bson import ObjectId

from utils.dtos.db import SearchGame
from utils.models import Game, GameRole, Lobby, Person, PersonGroup
from utils.services import GameService, LobbyService


def _make_game(name: str = "") -> Game:
    """Create a valid Game from a saved Lobby with players"""
    lobby = Lobby(
        name=name,
        people=PersonGroup(
            [
                Person(identifier="p1", roles={GameRole.ORGANIZER, GameRole.PLAYER}),
                Person(identifier="p2", roles={GameRole.PLAYER}),
            ]
        ),
    )
    LobbyService.save(lobby)
    return Game.from_lobby(lobby)


class TestGameService(TestCase):
    """Unit tests to ensure game service works as expected"""

    def test_save_game(self):
        """Game can be saved to the DB"""
        game = _make_game()

        self.assertIsNotNone(GameService.save(game))

    def test_get_game(self):
        """Game can be retrieved from the DB"""
        original_game = _make_game()
        GameService.save(original_game)
        assert original_game.id
        game = GameService.get(original_game.id)

        self.assertIsNotNone(game)
        self.assertEqual(game.id, original_game.id)

    def test_get_non_existent_game(self):
        """Unknown game cannot be retrieved from the DB"""
        self.assertRaises(ValueError, GameService.get, str(ObjectId()))

    def test_search_game(self):
        """Games can be searched in the DB"""
        text = f"search_test{ObjectId()}"
        games = [GameService.save(_make_game(name=f"{text} {i}")) for i in range(5)]

        found_games = GameService.search(
            SearchGame(
                name=text, client="p1", statuses=None, active_player=None, winner=None
            ),
            len(games) + 1,
        )

        self.assertEqual(len(found_games), len(games))
