'''Playing Game unit tests'''
from unittest import TestCase

import bid
import create_game
import discard
import play
import select_trump
import start_game
import suggestion
from app.dtos.client import PlaySuggestion, StartedGame, WaitingGame
from app.models import BidAmount, RoundStatus, SelectableSuit
from tests.helpers import build_request, read_response_body


class TestLobbyGame(TestCase):
    '''Unit tests to ensure games that are in progress behave as expected'''

    def test_perform_round_actions(self):
        '''A round of the game can be played'''
        resp = create_game.main(
            build_request(
                body={'name': 'play round test'}))
        created_game: WaitingGame = read_response_body(resp.get_body())
        resp = start_game.main(
            build_request(
                route_params={'game_id': created_game['id']},
                headers={'x-ms-client-principal-id': created_game['organizer']['identifier']}))
        game: StartedGame = read_response_body(resp.get_body())
        self.assertEqual(RoundStatus.BIDDING.name, game['status'])

        # bid
        resp = bid.main(
            build_request(
                route_params={'game_id': created_game['id']},
                body={
                    'amount': BidAmount.SHOOT_THE_MOON
                })
        )
        game: StartedGame = read_response_body(resp.get_body())

        self.assertEqual(RoundStatus.TRUMP_SELECTION.name, game['status'])

        # select trump
        resp = select_trump.main(
            build_request(
                route_params={'game_id': created_game['id']},
                body={
                    'suit': SelectableSuit.CLUBS.name
                })
        )
        game: StartedGame = read_response_body(resp.get_body())

        self.assertEqual(RoundStatus.DISCARD.name, game['status'])

        # discard
        resp = discard.main(
            build_request(
                route_params={'game_id': created_game['id']},
                body={
                    'cards': []
                })
        )
        game: StartedGame = read_response_body(resp.get_body())

        self.assertEqual(RoundStatus.TRICKS.name, game['status'])

        # ask for a suggestion so we know what card we can play
        resp = suggestion.main(
            build_request(
                route_params={'game_id': created_game['id']})
        )
        suggested_play: PlaySuggestion = read_response_body(resp.get_body())

        # play
        resp = play.main(
            build_request(
                route_params={'game_id': created_game['id']},
                body={
                    'card': suggested_play['card']
                })
        )
        game: StartedGame = read_response_body(resp.get_body())

        self.assertEqual(RoundStatus.TRICKS.name, game['status'])
        self.assertEqual(2, len(game['round']['tricks']))
