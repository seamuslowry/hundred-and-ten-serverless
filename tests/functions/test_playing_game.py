'''Playing Game unit tests'''
from unittest import TestCase

from functions.bid import bid as wrapped_bid
from functions.discard import discard as wrapped_discard
from functions.leave_game import leave_game as wrapped_leave_game
from functions.play import play as wrapped_play
from functions.rescind_prepass import rescind_prepass as wrapped_rescind_prepass
from functions.select_trump import select_trump as wrapped_select_trump
from utils.dtos.client import CompletedGame, StartedGame
from utils.models import BidAmount, RoundStatus, SelectableSuit
from tests.helpers import (build_request, get_suggestion, read_response_body,
                           started_game)


bid = wrapped_bid.build().get_user_function()
discard = wrapped_discard.build().get_user_function()
leave_game = wrapped_leave_game.build().get_user_function()
play = wrapped_play.build().get_user_function()
rescind_prepass = wrapped_rescind_prepass.build().get_user_function()
select_trump = wrapped_select_trump.build().get_user_function()


class TestPlayingGame(TestCase):
    '''Unit tests to ensure games that are in progress behave as expected'''

    def test_perform_round_actions(self):
        '''A round of the game can be played'''
        created_game: StartedGame = started_game()
        self.assertEqual(RoundStatus.BIDDING.name, created_game['status'])

        # assert that current suggestion is a bid
        suggested_bid = get_suggestion(created_game['id'])
        assert 'amount' in suggested_bid

        # bid
        resp = bid(
            build_request(
                route_params={'game_id': created_game['id']},
                body={
                    'amount': BidAmount.SHOOT_THE_MOON
                })
        )
        game: StartedGame = read_response_body(resp.get_body())

        self.assertEqual(RoundStatus.TRUMP_SELECTION.name, game['status'])

        # assert that current suggestion is a trump selection
        suggested_trump = get_suggestion(created_game['id'])
        assert 'suit' in suggested_trump

        # select trump
        resp = select_trump(
            build_request(
                route_params={'game_id': created_game['id']},
                body={
                    'suit': SelectableSuit.CLUBS.name
                })
        )
        game: StartedGame = read_response_body(resp.get_body())

        self.assertEqual(RoundStatus.DISCARD.name, game['status'])

        # assert that current suggestion is a discard
        suggested_discard = get_suggestion(created_game['id'])
        assert 'cards' in suggested_discard

        # discard
        resp = discard(
            build_request(
                route_params={'game_id': created_game['id']},
                body={
                    'cards': []
                })
        )
        game: StartedGame = read_response_body(resp.get_body())

        self.assertEqual(RoundStatus.TRICKS.name, game['status'])

        # ask for a suggestion so we know what card we can play
        suggested_play = get_suggestion(created_game['id'])
        assert 'card' in suggested_play

        # play
        resp = play(
            build_request(
                route_params={'game_id': created_game['id']},
                body={
                    'card': suggested_play['card']  # type: ignore
                })
        )
        game: StartedGame = read_response_body(resp.get_body())

        self.assertEqual(RoundStatus.TRICKS.name, game['status'])
        self.assertEqual(2, len(game['round']['tricks']))

    def test_prepass_and_rescind_prepass(self):
        '''A non-active player can prepass and rescind that prepass'''
        game: StartedGame = started_game()

        non_active_player = next(
            p for p in game['round']['players']
            if game['round']['active_player'] and p['identifier'] !=
            game['round']['active_player']['identifier'])

        # prepass
        resp = bid(
            build_request(
                route_params={'game_id': game['id']},
                headers={'x-ms-client-principal-id': non_active_player['identifier']},
                body={
                    'amount': BidAmount.PASS
                })
        )
        game: StartedGame = read_response_body(resp.get_body())
        non_active_player = next(p for p in game['round']
                                 ['players'] if p['identifier'] == non_active_player['identifier'])
        self.assertTrue(non_active_player['prepassed'])

        # rescind prepass
        resp = rescind_prepass(
            build_request(
                route_params={'game_id': game['id']},
                headers={'x-ms-client-principal-id': non_active_player['identifier']},
            )
        )
        game: StartedGame = read_response_body(resp.get_body())
        non_active_player = next(p for p in game['round']
                                 ['players'] if p['identifier'] == non_active_player['identifier'])
        self.assertFalse(non_active_player['prepassed'])

    def test_leave_playing_game(self):
        '''A player can leave an active game by automating themselves'''
        original_game: StartedGame = started_game()
        active_player = original_game['round']['active_player']
        assert active_player
        self.assertFalse(active_player['automate'])

        # leave
        resp = leave_game(
            build_request(
                route_params={'game_id': original_game['id']}
            )
        )
        game: CompletedGame = read_response_body(resp.get_body())
        active_player = next(p for p in game['players']
                             if p['identifier'] == active_player['identifier'])

        self.assertTrue(active_player['automate'])
