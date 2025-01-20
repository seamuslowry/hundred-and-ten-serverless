'''Game Service unit tests'''
from time import time
from unittest import TestCase

from utils.dtos.db import SearchGame
from utils.models import Game
from utils.services import GameService


class TestGameService(TestCase):
    '''Unit tests to ensure game service works as expected'''

    def test_save_game(self):
        '''Game can be saved to the DB'''
        game = Game(id=str(time()))

        self.assertIsNotNone(GameService.save(game))

    def test_get_game(self):
        '''Game can be retrieved to the DB'''
        original_game = Game(id=str(time()))
        GameService.save(original_game)
        game = GameService.get(original_game.id)

        self.assertIsNotNone(game)
        self.assertEqual(game.id, original_game.id)

    def test_get_non_existent_game(self):
        '''Unknown game cannot be retrieved to the DB'''
        original_game = Game(id=str(time()))

        self.assertRaises(ValueError, GameService.get, original_game.id)

    def test_search_game(self):
        '''Games can be searched in the DB'''
        text = f'search_test{time()}'
        games = [GameService.save(Game(id=str(time()), name=f'{text} {i}')) for i in range(5)]

        found_games = GameService.search(SearchGame(
            name=text,
            client='',
            statuses=None,
            active_player=None,
            winner=None
        ), len(games) + 1)

        self.assertEqual(games, found_games)
