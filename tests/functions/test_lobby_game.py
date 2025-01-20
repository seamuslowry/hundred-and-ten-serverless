'''Lobby Game unit tests'''
from unittest import TestCase

from function_app import (create_game as wrapped_create_game,
                          invite_to_game as wrapped_invite_to_game,
                          join_game as wrapped_join_game,
                          leave_game as wrapped_leave_game,
                          start_game as wrapped_start_game)
from utils.dtos.client import StartedGame, WaitingGame
from utils.models import GameStatus, RoundStatus
from tests.helpers import build_request, lobby_game, read_response_body

create_game = wrapped_create_game.build().get_user_function()
invite_to_game = wrapped_invite_to_game.build().get_user_function()
join_game = wrapped_join_game.build().get_user_function()
leave_game = wrapped_leave_game.build().get_user_function()
start_game = wrapped_start_game.build().get_user_function()


class TestLobbyGame(TestCase):
    '''Unit tests to ensure games that are waiting for players work as expected'''

    def test_create_game(self):
        '''New game can be created'''
        organizer = 'organizer'
        resp = create_game(
            build_request(
                headers={'x-ms-client-principal-id': organizer},
                body={'name': 'create test'}))
        game: WaitingGame = read_response_body(resp.get_body())

        self.assertEqual(organizer, game['organizer']['identifier'])
        self.assertEqual(0, len(game['players']))
        self.assertEqual(0, len(game['invitees']))
        self.assertEqual(GameStatus.WAITING_FOR_PLAYERS.name, game['status'])

    def test_organizer_invite_to_game(self):
        '''Organizer can be invite players to a game'''
        invitee = 'invitee'

        created_game: WaitingGame = lobby_game()

        resp = invite_to_game(
            build_request(
                route_params={'game_id': created_game['id']},
                headers={'x-ms-client-principal-id': created_game['organizer']['identifier']},
                body={'invitees': [invitee]}))
        invited_game: WaitingGame = read_response_body(resp.get_body())

        self.assertEqual(created_game['id'], invited_game['id'])
        self.assertEqual(0, len(invited_game['players']))
        self.assertEqual(1, len(invited_game['invitees']))
        self.assertEqual(invitee, invited_game['invitees'][0]['identifier'])
        self.assertEqual(GameStatus.WAITING_FOR_PLAYERS.name, invited_game['status'])

    def test_invitee_invite_to_game(self):
        '''Invited players cannot invite players to a game'''
        invitee = 'invitee'
        second_invitee = 'second'

        created_game: WaitingGame = lobby_game()

        # invite the original
        invite_to_game(
            build_request(
                route_params={'game_id': created_game['id']},
                headers={'x-ms-client-principal-id': created_game['organizer']['identifier']},
                body={'invitees': [invitee]}))

        # new invitee cannot invite
        failed_invite = invite_to_game(
            build_request(
                route_params={'game_id': created_game['id']},
                headers={'x-ms-client-principal-id': invitee},
                body={'invitees': [second_invitee]}))
        self.assertEqual(400, failed_invite.status_code)

    def test_player_invite_to_game(self):
        '''Players can invite other players to a game'''
        invitee = 'invitee'
        player = 'player'

        created_game: WaitingGame = lobby_game()

        # join as player
        join_game(
            build_request(
                route_params={'game_id': created_game['id']},
                headers={'x-ms-client-principal-id': player}))

        # new player can invite
        invite = invite_to_game(
            build_request(
                route_params={'game_id': created_game['id']},
                headers={'x-ms-client-principal-id': player},
                body={'invitees': [invitee]}))
        invited_game: WaitingGame = read_response_body(invite.get_body())

        self.assertEqual(created_game['id'], invited_game['id'])
        self.assertEqual(1, len(invited_game['players']))
        self.assertEqual(player, invited_game['players'][0]['identifier'])
        self.assertEqual(1, len(invited_game['invitees']))
        self.assertEqual(invitee, invited_game['invitees'][0]['identifier'])
        self.assertEqual(GameStatus.WAITING_FOR_PLAYERS.name, invited_game['status'])

    def test_join_public_game(self):
        '''Any player can join a public game'''
        player = 'player'

        created_game: WaitingGame = lobby_game()

        resp = join_game(
            build_request(
                route_params={'game_id': created_game['id']},
                headers={'x-ms-client-principal-id': player}))
        joined_game: WaitingGame = read_response_body(resp.get_body())

        self.assertEqual(created_game['id'], joined_game['id'])
        self.assertEqual(1, len(joined_game['players']))
        self.assertEqual(player, joined_game['players'][0]['identifier'])
        self.assertEqual(0, len(joined_game['invitees']))
        self.assertEqual(GameStatus.WAITING_FOR_PLAYERS.name, joined_game['status'])

    def test_join_private_game_uninvited(self):
        '''Uninvited players cannot join a private game'''
        player = 'player'

        resp = create_game(
            build_request(
                body={'name': 'private uninvited join test', 'accessibility': 'PRIVATE'}))
        created_game: WaitingGame = read_response_body(resp.get_body())

        resp = join_game(
            build_request(
                route_params={'game_id': created_game['id']},
                headers={'x-ms-client-principal-id': player}))
        self.assertEqual(400, resp.status_code)

    def test_join_private_game_invited(self):
        '''Invited players can join a private game'''
        player = 'player'

        resp = create_game(
            build_request(
                body={'name': 'private invite join test', 'accessibility': 'PRIVATE'}))
        created_game: WaitingGame = read_response_body(resp.get_body())

        resp = invite_to_game(
            build_request(
                route_params={'game_id': created_game['id']},
                headers={'x-ms-client-principal-id': created_game['organizer']['identifier']},
                body={'invitees': [player]}))

        resp = join_game(
            build_request(
                route_params={'game_id': created_game['id']},
                headers={'x-ms-client-principal-id': player}))

        joined_game: WaitingGame = read_response_body(resp.get_body())

        self.assertEqual(created_game['id'], joined_game['id'])
        self.assertEqual(1, len(joined_game['players']))
        self.assertEqual(player, joined_game['players'][0]['identifier'])
        self.assertEqual(0, len(joined_game['invitees']))
        self.assertEqual(GameStatus.WAITING_FOR_PLAYERS.name, joined_game['status'])

    def test_leave_game(self):
        '''Players can leave a game before it has started'''
        created_game: WaitingGame = lobby_game()

        resp = leave_game(
            build_request(
                route_params={'game_id': created_game['id']},
                headers={'x-ms-client-principal-id': created_game['organizer']['identifier']}))

        left_game: WaitingGame = read_response_body(resp.get_body())

        self.assertEqual(created_game['id'], left_game['id'])
        # organizer will always be populated, but will be dummy data when no real organizer exists
        self.assertNotEqual(
            created_game['organizer']['identifier'],
            left_game['organizer']['identifier'])
        self.assertEqual(0, len(left_game['players']))
        self.assertEqual(0, len(left_game['invitees']))
        self.assertEqual(GameStatus.WAITING_FOR_PLAYERS.name, left_game['status'])

    def test_player_start_game(self):
        '''Players cannot start the game'''
        player = 'player'

        created_game: WaitingGame = lobby_game()

        resp = join_game(
            build_request(
                route_params={'game_id': created_game['id']},
                headers={'x-ms-client-principal-id': player}))

        resp = start_game(
            build_request(
                route_params={'game_id': created_game['id']},
                headers={'x-ms-client-principal-id': player}))
        self.assertEqual(400, resp.status_code)

    def test_start_game(self):
        '''The organizer can start the game'''
        created_game: WaitingGame = lobby_game()

        resp = start_game(
            build_request(
                headers={'x-ms-client-principal-id': created_game['organizer']['identifier']},
                route_params={'game_id': created_game['id']}
            ))

        started_game: StartedGame = read_response_body(resp.get_body())

        self.assertEqual(created_game['id'], started_game['id'])
        self.assertEqual(4, len(started_game['round']['players']))
        self.assertEqual(RoundStatus.BIDDING.name, started_game['status'])
