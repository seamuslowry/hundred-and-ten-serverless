'''Games completed unit tests'''
import json
from unittest import TestCase, mock

from app.models import Game
from app.services import GameService
from search_won_games import main
from tests.helpers import DEFAULT_USER, build_request, read_response_body


class TestSearchWonGames(TestCase):
    '''Search Completed Game unit tests'''

    @mock.patch('search_won_games.parse_request',
                mock.Mock(return_value=(DEFAULT_USER, Game())))
    @mock.patch('app.services.GameService.search_won', return_value=[Game()])
    def test_get_games(self, search_games):
        '''On hitting the won games endpoint games are retrieved'''
        req = build_request(body=json.dumps({}).encode('utf-8'))

        resp = main(req)
        resp_list = read_response_body(resp.get_body())

        self.assertEqual(
            list(map(lambda g: GameService.json(g, ''), search_games.return_value)), resp_list)
