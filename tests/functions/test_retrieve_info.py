'''Retrieve Info unit tests'''
from time import time
from unittest import TestCase

from functions.events import events as wrapped_events
from functions.game_info import game_info as wrapped_game_info
from functions.join_game import join_game as wrapped_join_game
from functions.players import players as wrapped_players
from functions.search_games import search_games as wrapped_search_games
from functions.search_users import search_users as wrapped_search_users
from utils.dtos.client import CompletedGame, Event, User, WaitingGame
from utils.mappers.constants import EventType
from tests.helpers import (build_request, completed_game, create_user,
                           lobby_game, read_response_body, request_suggestion,
                           started_game)


events = wrapped_events.build().get_user_function()
game_info = wrapped_game_info.build().get_user_function()
join_game = wrapped_join_game.build().get_user_function()
players = wrapped_players.build().get_user_function()
search_games = wrapped_search_games.build().get_user_function()
search_users = wrapped_search_users.build().get_user_function()


class TestRetrieveInfo(TestCase):
    '''Unit tests to the client can query for info as necessary'''

    def test_search_winner(self):
        '''Can search by winner'''
        game: CompletedGame = completed_game()

        # search games
        resp = search_games(
            build_request(
                body={
                    'winner': game['winner']['identifier']
                })
        )
        games = read_response_body(resp.get_body())
        self.assertIn(game['id'], list(map(lambda g: g['id'], games)))

    def test_game_info(self):
        '''Can retrieve information about a game'''
        original_game: CompletedGame = completed_game()

        # get that game's info
        resp = game_info(
            build_request(
                route_params={'game_id': original_game['id']})
        )
        game = read_response_body(resp.get_body())
        self.assertEqual(game['id'], original_game['id'])

    def test_game_events(self):
        '''Can retrieve event information about a game'''
        original_game: CompletedGame = completed_game()

        # get that game's events
        resp = events(
            build_request(
                route_params={'game_id': original_game['id']})
        )
        retrieved_events: list[Event] = read_response_body(resp.get_body())
        self.assertIsNotNone(original_game['results'])
        assert original_game['results']
        self.assertNotEqual(original_game['results'], [])
        self.assertGreaterEqual(len(retrieved_events), len(original_game['results']))
        self.assertEqual(
            retrieved_events[len(retrieved_events)-len(original_game['results']):],
            original_game['results'])
        self.assertEqual(retrieved_events[-1]['type'], EventType.GAME_END.name)

    def test_game_players(self):
        '''Can retrieve user information for players on a game'''
        original_game: WaitingGame = lobby_game()
        other_player_ids = list(map(lambda i: f'{time()}-{i}', range(1, 4)))

        organizer: User = create_user(original_game['organizer']['identifier'])
        other_players: list[User] = list(map(create_user, other_player_ids))

        for player in other_players:
            join_game(
                build_request(
                    route_params={'game_id': original_game['id']},
                    headers={'x-ms-client-principal-id': player['identifier']}))

        # get that game's players
        resp = players(
            build_request(
                route_params={'game_id': original_game['id']})
        )
        retrieved_users: list[User] = read_response_body(resp.get_body())

        self.assertEqual(4, len(retrieved_users))
        self.assertEqual(
            [organizer['identifier']] + other_player_ids,
            list(map(lambda p: p['identifier'],
                     retrieved_users)))

    def test_search_users(self):
        '''Can retrieve user information by substring of name'''
        # create new unique users
        timestamp = time()
        user_one = (f'{timestamp}one', f'{timestamp}aaa')
        user_two = (f'{timestamp}two', f'{timestamp}AAA')
        user_three = (f'{timestamp}three', f'{timestamp}bbb')
        create_user(user_one[0], user_one[1])
        create_user(user_two[0], user_two[1])
        create_user(user_three[0], user_three[1])

        # get users
        resp = search_users(
            build_request(
                params={
                    'searchText': 'aaa'
                })
        )
        retrieved_users: list[User] = read_response_body(resp.get_body())
        retrieved_user_ids = list(map(lambda u: u['identifier'], retrieved_users))
        self.assertIn(user_one[0], retrieved_user_ids)
        self.assertIn(user_two[0], retrieved_user_ids)
        self.assertNotIn(user_three[0], retrieved_user_ids)

    def test_get_suggestion_on_other_turn(self):
        '''The game will not provide a suggestion on another player's turn'''
        game = started_game()
        active_player = game['round']['active_player']
        assert active_player
        non_active_player = next(
            p for p in game['round']['players'] if p['identifier'] != active_player['identifier'])
        resp = request_suggestion(game['id'], non_active_player['identifier'])

        self.assertEqual(400, resp.status_code)
