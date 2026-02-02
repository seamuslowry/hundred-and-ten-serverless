"""Game Service unit tests"""

from time import time
from unittest import TestCase

from utils.dtos.db import SearchGame
from utils.models import Bid, BidAmount, Game, GameRole, GameStatus, Person
from utils.models.game import PersonGroup
from utils.services import GameService


class TestGameService(TestCase):
    """Unit tests to ensure game service works as expected"""

    def test_save_game(self):
        """Game can be saved to the DB"""
        game = Game(id=str(time()))

        self.assertIsNotNone(GameService.save(game))

    def test_get_game(self):
        """Game can be retrieved to the DB"""
        original_game = Game(id=str(time()))
        GameService.save(original_game)
        game = GameService.get(original_game.id)

        self.assertIsNotNone(game)
        self.assertEqual(game.id, original_game.id)

    def test_get_non_existent_game(self):
        """Unknown game cannot be retrieved to the DB"""
        original_game = Game(id=str(time()))

        self.assertRaises(ValueError, GameService.get, original_game.id)

    def test_search_game(self):
        """Games can be searched in the DB"""
        text = f"search_test{time()}"
        games = [
            GameService.save(Game(id=str(time()), name=f"{text} {i}")) for i in range(5)
        ]

        found_games = GameService.search(
            SearchGame(
                name=text, client="", statuses=None, active_player=None, winner=None
            ),
            len(games) + 1,
        )

        self.assertEqual(games, found_games)

    def test_save_and_get_started_game_with_moves(self):
        """Started games with moves can be saved and retrieved correctly"""
        game = Game(
            id=str(time()),
            name="Test Game",
            seed="test-seed",
            people=PersonGroup(
                [
                    Person(
                        identifier="player1", roles={GameRole.ORGANIZER, GameRole.PLAYER}
                    ),
                    Person(identifier="player2", roles={GameRole.PLAYER}),
                ]
            ),
        )
        game.start_game()

        # Perform a bid action with the active player
        active_player = game.active_round.active_player
        assert active_player
        game.act(Bid(identifier=active_player.identifier, amount=BidAmount.PASS))

        GameService.save(game)
        restored = GameService.get(game.id)

        self.assertEqual(restored.id, game.id)
        self.assertFalse(restored.lobby)
        self.assertEqual(len(restored.moves), 1)
        self.assertIsInstance(restored.moves[0], Bid)

    def test_search_by_status(self):
        """Games can be filtered by status"""
        text = f"status_test{time()}"

        # Create a lobby game (WAITING_FOR_PLAYERS)
        lobby_game = Game(
            id=str(time()),
            name=f"{text} lobby",
            people=PersonGroup(
                [
                    Person(
                        identifier="player1", roles={GameRole.ORGANIZER, GameRole.PLAYER}
                    ),
                    Person(identifier="player2", roles={GameRole.PLAYER}),
                ]
            ),
        )
        GameService.save(lobby_game)

        # Create a started game (BIDDING status)
        started_game = Game(
            id=str(time()) + "started",
            name=f"{text} started",
            people=PersonGroup(
                [
                    Person(
                        identifier="player1", roles={GameRole.ORGANIZER, GameRole.PLAYER}
                    ),
                    Person(identifier="player2", roles={GameRole.PLAYER}),
                ]
            ),
        )
        started_game.start_game()
        GameService.save(started_game)

        # Search for only WAITING_FOR_PLAYERS games
        found = GameService.search(
            SearchGame(
                name=text,
                client="player1",
                statuses=[GameStatus.WAITING_FOR_PLAYERS.name],
                active_player=None,
                winner=None,
            ),
            10,
        )

        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].id, lobby_game.id)

    def test_search_by_active_player(self):
        """Games can be filtered by active player"""
        text = f"active_test{time()}"

        # Create a started game
        game = Game(
            id=str(time()),
            name=text,
            people=PersonGroup(
                [
                    Person(
                        identifier="player1", roles={GameRole.ORGANIZER, GameRole.PLAYER}
                    ),
                    Person(identifier="player2", roles={GameRole.PLAYER}),
                ]
            ),
        )
        game.start_game()
        GameService.save(game)

        active_player = game.active_round.active_player
        assert active_player
        non_active = "player1" if active_player.identifier == "player2" else "player2"

        # Search for games where active_player is the active player
        found = GameService.search(
            SearchGame(
                name=text,
                client="player1",
                statuses=None,
                active_player=active_player.identifier,
                winner=None,
            ),
            10,
        )
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].id, game.id)

        # Search for games where non_active is the active player (should be empty)
        not_found = GameService.search(
            SearchGame(
                name=text,
                client="player1",
                statuses=None,
                active_player=non_active,
                winner=None,
            ),
            10,
        )
        self.assertEqual(len(not_found), 0)
