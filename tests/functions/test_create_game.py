'''Create game unit tests'''
from unittest import TestCase, mock

from create_game import main
from models import Game
from services import GameService
from tests.helpers import DEFAULT_ID, build_request, read_response_body


class TestCreateGame(TestCase):
    '''Create Game unit tests'''

    @mock.patch('services.GameService.save', return_value={})
    def test_creates_game(self, save):
        '''On hitting the create request a game is created and returned'''
        req = build_request()
        saved_value = Game()

        save.return_value = saved_value

        resp = main(req)

        save.assert_called_once()
        self.assertEqual(
            read_response_body(resp.get_body()),
            GameService.json(saved_value, DEFAULT_ID))
