'''Start game unit tests'''
from unittest import TestCase, mock

from models import Game, GameRole, Group, Person
from start_game import main
from tests.helpers import (DEFAULT_ID, DEFAULT_USER, build_request,
                           read_response_body, return_input)


class TestStartGame(TestCase):
    '''Start Game unit tests'''

    @mock.patch('services.GameService.save', side_effect=return_input)
    @mock.patch('services.UserService.save', mock.Mock(side_effect=return_input))
    @mock.patch(
        'services.GameService.get', mock.Mock(
            return_value=Game(
                people=Group(
                    [Person(DEFAULT_ID, roles={GameRole.PLAYER}),
                     Person(DEFAULT_ID + '2', roles={GameRole.PLAYER})]))))
    @mock.patch('services.UserService.get', mock.Mock(return_value=DEFAULT_USER))
    def test_starts_game_if_organizer(self, game_save):
        '''When the organizer hits the start endpoint the game begins'''
        req = build_request(route_params={'id': 'id'})

        resp = main(req)
        resp_dict = read_response_body(resp.get_body())

        game_save.assert_called_once()
        self.assertIn('round', resp_dict)

    @mock.patch('services.GameService.save', side_effect=return_input)
    @mock.patch('services.UserService.save', mock.Mock(side_effect=return_input))
    @mock.patch(
        'services.GameService.get', mock.Mock(
            return_value=Game(
                people=Group(
                    [Person(DEFAULT_ID + '1', roles={GameRole.PLAYER}),
                     Person(DEFAULT_ID + '2', roles={GameRole.PLAYER})]))))
    @mock.patch('services.UserService.get', mock.Mock(return_value=DEFAULT_USER))
    def test_starts_game_if_not_organizer(self, game_save):
        '''When someone not organizer hits the start endpoint, nothing happens'''
        req = build_request(route_params={'id': 'id'})

        resp = main(req)
        resp_dict = read_response_body(resp.get_body())

        game_save.assert_called_once()
        self.assertNotIn('round', resp_dict)