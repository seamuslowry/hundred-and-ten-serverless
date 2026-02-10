"""Lobby unit tests"""

from unittest import TestCase

from function_app import (
    create_lobby as wrapped_create_lobby,
)
from function_app import (
    invite_to_lobby as wrapped_invite_to_lobby,
)
from function_app import (
    join_lobby as wrapped_join_lobby,
)
from function_app import (
    leave_lobby as wrapped_leave_lobby,
)
from function_app import lobby_info as wrapped_lobby_info
from function_app import (
    search_lobbies as wrapped_search_lobbies,
)
from function_app import (
    start_game as wrapped_start_game,
)
from tests.helpers import build_request, lobby_game, read_response_body
from utils.dtos.client import StartedGame, WaitingGame
from utils.models import GameStatus, RoundStatus

lobby_info = wrapped_lobby_info.build().get_user_function()
create_lobby = wrapped_create_lobby.build().get_user_function()
invite_to_lobby = wrapped_invite_to_lobby.build().get_user_function()
join_lobby = wrapped_join_lobby.build().get_user_function()
leave_lobby = wrapped_leave_lobby.build().get_user_function()
search_lobbies = wrapped_search_lobbies.build().get_user_function()
start_game = wrapped_start_game.build().get_user_function()


class TestLobby(TestCase):
    """Unit tests to ensure lobbies work as expected"""

    def test_lobby_info_invalid_id(self):
        """Invalid lobby ID returns 400"""
        resp = lobby_info(build_request(route_params={"lobby_id": "not-an-id"}))
        self.assertEqual(400, resp.status_code)

    def test_lobby_info(self):
        """Invalid lobby ID returns 400"""
        lobby: WaitingGame = lobby_game()
        resp = lobby_info(build_request(route_params={"lobby_id": lobby["id"]}))

        retrieved_lobby_info: WaitingGame = read_response_body(resp.get_body())

        self.assertIsNotNone(retrieved_lobby_info["id"])
        self.assertIsNotNone(retrieved_lobby_info["name"])
        self.assertIsNotNone(retrieved_lobby_info["organizer"])
        self.assertEqual([], retrieved_lobby_info["players"])
        self.assertEqual([], retrieved_lobby_info["invitees"])

    def test_create_lobby(self):
        """New lobby can be created"""
        organizer = "organizer"
        resp = create_lobby(
            build_request(
                headers={"x-ms-client-principal-id": organizer},
                body={"name": "create test"},
            )
        )
        lobby: WaitingGame = read_response_body(resp.get_body())

        self.assertEqual(organizer, lobby["organizer"]["identifier"])
        self.assertEqual(0, len(lobby["players"]))
        self.assertEqual(0, len(lobby["invitees"]))
        self.assertEqual(GameStatus.WAITING_FOR_PLAYERS.name, lobby["status"])

    def test_organizer_invite_to_lobby(self):
        """Organizer can invite players to a lobby"""
        invitee = "invitee"

        created_lobby: WaitingGame = lobby_game()

        resp = invite_to_lobby(
            build_request(
                route_params={"lobby_id": created_lobby["id"]},
                headers={
                    "x-ms-client-principal-id": created_lobby["organizer"]["identifier"]
                },
                body={"invitees": [invitee]},
            )
        )
        invited_lobby: WaitingGame = read_response_body(resp.get_body())

        self.assertEqual(created_lobby["id"], invited_lobby["id"])
        self.assertEqual(0, len(invited_lobby["players"]))
        self.assertEqual(1, len(invited_lobby["invitees"]))
        self.assertEqual(invitee, invited_lobby["invitees"][0]["identifier"])
        self.assertEqual(GameStatus.WAITING_FOR_PLAYERS.name, invited_lobby["status"])

    def test_invitee_invite_to_lobby(self):
        """Invited players cannot invite players to a lobby"""
        invitee = "invitee"
        second_invitee = "second"

        created_lobby: WaitingGame = lobby_game()

        # invite the original
        invite_to_lobby(
            build_request(
                route_params={"lobby_id": created_lobby["id"]},
                headers={
                    "x-ms-client-principal-id": created_lobby["organizer"]["identifier"]
                },
                body={"invitees": [invitee]},
            )
        )

        # new invitee cannot invite
        failed_invite = invite_to_lobby(
            build_request(
                route_params={"lobby_id": created_lobby["id"]},
                headers={"x-ms-client-principal-id": invitee},
                body={"invitees": [second_invitee]},
            )
        )
        self.assertEqual(400, failed_invite.status_code)

    def test_player_invite_to_lobby(self):
        """Players can invite other players to a lobby"""
        invitee = "invitee"
        player = "player"

        created_lobby: WaitingGame = lobby_game()

        # join as player
        join_lobby(
            build_request(
                route_params={"lobby_id": created_lobby["id"]},
                headers={"x-ms-client-principal-id": player},
            )
        )

        # new player can invite
        invite = invite_to_lobby(
            build_request(
                route_params={"lobby_id": created_lobby["id"]},
                headers={"x-ms-client-principal-id": player},
                body={"invitees": [invitee]},
            )
        )
        invited_lobby: WaitingGame = read_response_body(invite.get_body())

        self.assertEqual(created_lobby["id"], invited_lobby["id"])
        self.assertEqual(1, len(invited_lobby["players"]))
        self.assertEqual(player, invited_lobby["players"][0]["identifier"])
        self.assertEqual(1, len(invited_lobby["invitees"]))
        self.assertEqual(invitee, invited_lobby["invitees"][0]["identifier"])
        self.assertEqual(GameStatus.WAITING_FOR_PLAYERS.name, invited_lobby["status"])

    def test_join_public_lobby(self):
        """Any player can join a public lobby"""
        player = "player"

        created_lobby: WaitingGame = lobby_game()

        resp = join_lobby(
            build_request(
                route_params={"lobby_id": created_lobby["id"]},
                headers={"x-ms-client-principal-id": player},
            )
        )
        joined_lobby: WaitingGame = read_response_body(resp.get_body())

        self.assertEqual(created_lobby["id"], joined_lobby["id"])
        self.assertEqual(1, len(joined_lobby["players"]))
        self.assertEqual(player, joined_lobby["players"][0]["identifier"])
        self.assertEqual(0, len(joined_lobby["invitees"]))
        self.assertEqual(GameStatus.WAITING_FOR_PLAYERS.name, joined_lobby["status"])

    def test_join_private_lobby_uninvited(self):
        """Uninvited players cannot join a private lobby"""
        player = "player"

        resp = create_lobby(
            build_request(
                body={"name": "private uninvited join test", "accessibility": "PRIVATE"}
            )
        )
        created_lobby: WaitingGame = read_response_body(resp.get_body())

        resp = join_lobby(
            build_request(
                route_params={"lobby_id": created_lobby["id"]},
                headers={"x-ms-client-principal-id": player},
            )
        )
        self.assertEqual(400, resp.status_code)

    def test_join_private_lobby_invited(self):
        """Invited players can join a private lobby"""
        player = "player"

        resp = create_lobby(
            build_request(
                body={"name": "private invite join test", "accessibility": "PRIVATE"}
            )
        )
        created_lobby: WaitingGame = read_response_body(resp.get_body())

        invite_to_lobby(
            build_request(
                route_params={"lobby_id": created_lobby["id"]},
                headers={
                    "x-ms-client-principal-id": created_lobby["organizer"]["identifier"]
                },
                body={"invitees": [player]},
            )
        )

        resp = join_lobby(
            build_request(
                route_params={"lobby_id": created_lobby["id"]},
                headers={"x-ms-client-principal-id": player},
            )
        )

        joined_lobby: WaitingGame = read_response_body(resp.get_body())

        self.assertEqual(created_lobby["id"], joined_lobby["id"])
        self.assertEqual(1, len(joined_lobby["players"]))
        self.assertEqual(player, joined_lobby["players"][0]["identifier"])
        self.assertEqual(0, len(joined_lobby["invitees"]))
        self.assertEqual(GameStatus.WAITING_FOR_PLAYERS.name, joined_lobby["status"])

    def test_leave_lobby(self):
        """Any player can join a public lobby"""
        player = "player"

        created_lobby: WaitingGame = lobby_game()

        resp = join_lobby(
            build_request(
                route_params={"lobby_id": created_lobby["id"]},
                headers={"x-ms-client-principal-id": player},
            )
        )
        joined_lobby: WaitingGame = read_response_body(resp.get_body())

        self.assertEqual(created_lobby["id"], joined_lobby["id"])
        self.assertEqual(1, len(joined_lobby["players"]))
        self.assertEqual(player, joined_lobby["players"][0]["identifier"])

        resp = leave_lobby(
            build_request(
                route_params={"lobby_id": created_lobby["id"]},
                headers={"x-ms-client-principal-id": player},
            )
        )

        left_lobby: WaitingGame = read_response_body(resp.get_body())

        self.assertEqual(created_lobby["id"], left_lobby["id"])
        self.assertEqual(
            created_lobby["organizer"]["identifier"],
            left_lobby["organizer"]["identifier"],
        )
        self.assertEqual(0, len(left_lobby["players"]))
        self.assertEqual(GameStatus.WAITING_FOR_PLAYERS.name, left_lobby["status"])

    def test_player_start_game(self):
        """Players cannot start the game"""
        player = "player"

        created_lobby: WaitingGame = lobby_game()

        join_lobby(
            build_request(
                route_params={"lobby_id": created_lobby["id"]},
                headers={"x-ms-client-principal-id": player},
            )
        )

        resp = start_game(
            build_request(
                route_params={"lobby_id": created_lobby["id"]},
                headers={"x-ms-client-principal-id": player},
            )
        )
        self.assertEqual(400, resp.status_code)

    def test_start_game(self):
        """The organizer can start the game"""
        created_lobby: WaitingGame = lobby_game()

        resp = start_game(
            build_request(
                headers={
                    "x-ms-client-principal-id": created_lobby["organizer"]["identifier"]
                },
                route_params={"lobby_id": created_lobby["id"]},
            )
        )

        game: StartedGame = read_response_body(resp.get_body())

        self.assertEqual(created_lobby["id"], game["id"])
        self.assertEqual(4, len(game["round"]["players"]))
        self.assertEqual(RoundStatus.BIDDING.name, game["status"])

    def test_unknown_user_cannot_invite(self):
        """A user not in the lobby cannot invite others"""
        unknown_user = "unknown_user"
        invitee = "invitee"

        created_lobby: WaitingGame = lobby_game()

        # Unknown user tries to invite - should fail because they're not in the lobby
        resp = invite_to_lobby(
            build_request(
                route_params={"lobby_id": created_lobby["id"]},
                headers={"x-ms-client-principal-id": unknown_user},
                body={"invitees": [invitee]},
            )
        )
        self.assertEqual(400, resp.status_code)

    def test_unknown_player_leaves_fails(self):
        """When an unknown player leaves, return 400 because they're not in the lobby"""
        player = "player"

        created_lobby: WaitingGame = lobby_game()

        # Unrecognized player attempts to leave
        resp = leave_lobby(
            build_request(
                route_params={"lobby_id": created_lobby["id"]},
                headers={"x-ms-client-principal-id": player},
            )
        )

        self.assertEqual(400, resp.status_code)

    def test_organizer_leaves_fails(self):
        """When organizer attempts to leave, prevent it"""
        player = "player"

        created_lobby: WaitingGame = lobby_game()

        # Another player joins
        join_lobby(
            build_request(
                route_params={"lobby_id": created_lobby["id"]},
                headers={"x-ms-client-principal-id": player},
            )
        )

        # Organizer attempts to leave
        resp = leave_lobby(
            build_request(
                route_params={"lobby_id": created_lobby["id"]},
                headers={
                    "x-ms-client-principal-id": created_lobby["organizer"]["identifier"]
                },
            )
        )

        # Organizer cannot leave. Needs to delete lobby.
        self.assertEqual(400, resp.status_code)

    def test_search_lobbies(self):
        """Can search for lobbies"""
        created_lobby: WaitingGame = lobby_game()

        resp = search_lobbies(
            build_request(
                method="GET",
                headers={
                    "x-ms-client-principal-id": created_lobby["organizer"]["identifier"]
                },
                body={"searchText": "test"},
            )
        )

        lobbies = read_response_body(resp.get_body())
        self.assertGreaterEqual(len(lobbies), 1)
