"""Lobby unit tests"""

from unittest import TestCase

from tests.helpers import get_client, lobby_game
from utils.models import GameStatus, RoundStatus


class TestLobby(TestCase):
    """Unit tests to ensure lobbies work as expected"""

    def test_lobby_info_invalid_id(self):
        """Invalid lobby ID returns 400"""
        client = get_client()
        resp = client.get(
            "/lobby/not-an-id",
            headers={"authorization": "Bearer id"},
        )
        self.assertEqual(400, resp.status_code)

    def test_lobby_info(self):
        """Invalid lobby ID returns 400"""
        client = get_client()
        lobby = lobby_game()
        resp = client.get(
            f"/lobby/{lobby['id']}",
            headers={"authorization": "Bearer id"},
        )

        retrieved_lobby_info = resp.json()

        self.assertIsNotNone(retrieved_lobby_info["id"])
        self.assertIsNotNone(retrieved_lobby_info["name"])
        self.assertIsNotNone(retrieved_lobby_info["organizer"])
        self.assertEqual([], retrieved_lobby_info["players"])
        self.assertEqual([], retrieved_lobby_info["invitees"])

    def test_create_lobby(self):
        """New lobby can be created"""
        client = get_client()
        organizer = "organizer"
        resp = client.post(
            "/create",
            json={"name": "create test"},
            headers={"authorization": f"Bearer {organizer}"},
        )
        lobby = resp.json()

        self.assertEqual(organizer, lobby["organizer"]["identifier"])
        self.assertEqual(0, len(lobby["players"]))
        self.assertEqual(0, len(lobby["invitees"]))
        self.assertEqual(GameStatus.WAITING_FOR_PLAYERS.name, lobby["status"])

    def test_organizer_invite_to_lobby(self):
        """Organizer can invite players to a lobby"""
        client = get_client()
        invitee = "invitee"

        created_lobby = lobby_game()

        resp = client.post(
            f"/invite/{created_lobby['id']}",
            json={"invitees": [invitee]},
            headers={
                "authorization": f"Bearer {created_lobby['organizer']['identifier']}"
            },
        )
        invited_lobby = resp.json()

        self.assertEqual(created_lobby["id"], invited_lobby["id"])
        self.assertEqual(0, len(invited_lobby["players"]))
        self.assertEqual(1, len(invited_lobby["invitees"]))
        self.assertEqual(invitee, invited_lobby["invitees"][0]["identifier"])
        self.assertEqual(GameStatus.WAITING_FOR_PLAYERS.name, invited_lobby["status"])

    def test_invitee_invite_to_lobby(self):
        """Invited players cannot invite players to a lobby"""
        client = get_client()
        invitee = "invitee"
        second_invitee = "second"

        created_lobby = lobby_game()

        # invite the original
        client.post(
            f"/invite/{created_lobby['id']}",
            json={"invitees": [invitee]},
            headers={
                "authorization": f"Bearer {created_lobby['organizer']['identifier']}"
            },
        )

        # new invitee cannot invite
        failed_invite = client.post(
            f"/invite/{created_lobby['id']}",
            json={"invitees": [second_invitee]},
            headers={"authorization": f"Bearer {invitee}"},
        )
        self.assertEqual(400, failed_invite.status_code)

    def test_player_invite_to_lobby(self):
        """Players can invite other players to a lobby"""
        client = get_client()
        invitee = "invitee"
        player = "player"

        created_lobby = lobby_game()

        # join as player
        client.post(
            f"/join/{created_lobby['id']}",
            headers={"authorization": f"Bearer {player}"},
        )

        # new player can invite
        invite = client.post(
            f"/invite/{created_lobby['id']}",
            json={"invitees": [invitee]},
            headers={"authorization": f"Bearer {player}"},
        )
        invited_lobby = invite.json()

        self.assertEqual(created_lobby["id"], invited_lobby["id"])
        self.assertEqual(1, len(invited_lobby["players"]))
        self.assertEqual(player, invited_lobby["players"][0]["identifier"])
        self.assertEqual(1, len(invited_lobby["invitees"]))
        self.assertEqual(invitee, invited_lobby["invitees"][0]["identifier"])
        self.assertEqual(GameStatus.WAITING_FOR_PLAYERS.name, invited_lobby["status"])

    def test_join_public_lobby(self):
        """Any player can join a public lobby"""
        client = get_client()
        player = "player"

        created_lobby = lobby_game()

        resp = client.post(
            f"/join/{created_lobby['id']}",
            headers={"authorization": f"Bearer {player}"},
        )
        joined_lobby = resp.json()

        self.assertEqual(created_lobby["id"], joined_lobby["id"])
        self.assertEqual(1, len(joined_lobby["players"]))
        self.assertEqual(player, joined_lobby["players"][0]["identifier"])
        self.assertEqual(0, len(joined_lobby["invitees"]))
        self.assertEqual(GameStatus.WAITING_FOR_PLAYERS.name, joined_lobby["status"])

    def test_join_private_lobby_uninvited(self):
        """Uninvited players cannot join a private lobby"""
        client = get_client()
        organizer = "organizer"
        player = "player"

        resp = client.post(
            "/create",
            json={"name": "private uninvited join test", "accessibility": "PRIVATE"},
            headers={"authorization": f"Bearer {organizer}"},
        )
        created_lobby = resp.json()

        resp = client.post(
            f"/join/{created_lobby['id']}",
            headers={"authorization": f"Bearer {player}"},
        )
        self.assertEqual(400, resp.status_code)

    def test_join_private_lobby_invited(self):
        """Invited players can join a private lobby"""
        client = get_client()
        organizer = "organizer"
        player = "player"

        resp = client.post(
            "/create",
            json={"name": "private invite join test", "accessibility": "PRIVATE"},
            headers={"authorization": f"Bearer {organizer}"},
        )
        created_lobby = resp.json()

        client.post(
            f"/invite/{created_lobby['id']}",
            json={"invitees": [player]},
            headers={
                "authorization": f"Bearer {created_lobby['organizer']['identifier']}"
            },
        )

        resp = client.post(
            f"/join/{created_lobby['id']}",
            headers={"authorization": f"Bearer {player}"},
        )

        joined_lobby = resp.json()

        self.assertEqual(created_lobby["id"], joined_lobby["id"])
        self.assertEqual(1, len(joined_lobby["players"]))
        self.assertEqual(player, joined_lobby["players"][0]["identifier"])
        self.assertEqual(0, len(joined_lobby["invitees"]))
        self.assertEqual(GameStatus.WAITING_FOR_PLAYERS.name, joined_lobby["status"])

    def test_leave_lobby(self):
        """Any player can join a public lobby"""
        client = get_client()
        player = "player"

        created_lobby = lobby_game()

        resp = client.post(
            f"/join/{created_lobby['id']}",
            headers={"authorization": f"Bearer {player}"},
        )
        joined_lobby = resp.json()

        self.assertEqual(created_lobby["id"], joined_lobby["id"])
        self.assertEqual(1, len(joined_lobby["players"]))
        self.assertEqual(player, joined_lobby["players"][0]["identifier"])

        resp = client.post(
            f"/leave/lobby/{created_lobby['id']}",
            headers={"authorization": f"Bearer {player}"},
        )

        left_lobby = resp.json()

        self.assertEqual(created_lobby["id"], left_lobby["id"])
        self.assertEqual(
            created_lobby["organizer"]["identifier"],
            left_lobby["organizer"]["identifier"],
        )
        self.assertEqual(0, len(left_lobby["players"]))
        self.assertEqual(GameStatus.WAITING_FOR_PLAYERS.name, left_lobby["status"])

    def test_player_start_game(self):
        """Players cannot start the game"""
        client = get_client()
        player = "player"

        created_lobby = lobby_game()

        client.post(
            f"/join/{created_lobby['id']}",
            headers={"authorization": f"Bearer {player}"},
        )

        resp = client.post(
            f"/start/{created_lobby['id']}",
            headers={"authorization": f"Bearer {player}"},
        )
        self.assertEqual(400, resp.status_code)

    def test_start_game(self):
        """The organizer can start the game"""
        client = get_client()
        created_lobby = lobby_game()

        resp = client.post(
            f"/start/{created_lobby['id']}",
            headers={
                "authorization": f"Bearer {created_lobby['organizer']['identifier']}"
            },
        )

        game = resp.json()

        self.assertEqual(created_lobby["id"], game["id"])
        self.assertEqual(4, len(game["round"]["players"]))
        self.assertEqual(RoundStatus.BIDDING.name, game["status"])

    def test_unknown_user_cannot_invite(self):
        """A user not in the lobby cannot invite others"""
        client = get_client()
        unknown_user = "unknown_user"
        invitee = "invitee"

        created_lobby = lobby_game()

        # Unknown user tries to invite - should fail because they're not in the lobby
        resp = client.post(
            f"/invite/{created_lobby['id']}",
            json={"invitees": [invitee]},
            headers={"authorization": f"Bearer {unknown_user}"},
        )
        self.assertEqual(400, resp.status_code)

    def test_unknown_player_leaves_fails(self):
        """When an unknown player leaves, return 400 because they're not in the lobby"""
        client = get_client()
        player = "player"

        created_lobby = lobby_game()

        # Unrecognized player attempts to leave
        resp = client.post(
            f"/leave/lobby/{created_lobby['id']}",
            headers={"authorization": f"Bearer {player}"},
        )

        self.assertEqual(400, resp.status_code)

    def test_organizer_leaves_fails(self):
        """When organizer attempts to leave, prevent it"""
        client = get_client()
        player = "player"

        created_lobby = lobby_game()

        # Another player joins
        client.post(
            f"/join/{created_lobby['id']}",
            headers={"authorization": f"Bearer {player}"},
        )

        # Organizer attempts to leave
        resp = client.post(
            f"/leave/lobby/{created_lobby['id']}",
            headers={
                "authorization": f"Bearer {created_lobby['organizer']['identifier']}"
            },
        )

        # Organizer cannot leave. Needs to delete lobby.
        self.assertEqual(400, resp.status_code)

    def test_search_lobbies(self):
        """Can search for lobbies"""
        client = get_client()
        created_lobby = lobby_game()

        resp = client.post(
            "/lobbies",
            json={"searchText": "test"},
            headers={
                "authorization": f"Bearer {created_lobby['organizer']['identifier']}"
            },
        )

        lobbies = resp.json()
        self.assertGreaterEqual(len(lobbies), 1)
