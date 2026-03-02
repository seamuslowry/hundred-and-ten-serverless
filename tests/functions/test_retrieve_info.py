"""Retrieve Info unit tests"""

from time import time
from unittest import TestCase

from tests.helpers import (
    DEFAULT_ID,
    completed_game,
    create_user,
    get_client,
    lobby_game,
    request_suggestion,
    started_game,
)


class TestRetrieveInfo(TestCase):
    """Unit tests to the client can query for info as necessary"""

    def test_search_winner(self):
        """Can search by winner"""
        client = get_client()
        game = completed_game()

        # search games
        resp = client.post(
            "/games",
            json={"winner": game["winner"]["identifier"]},
            headers={"authorization": f"Bearer {DEFAULT_ID}"},
        )
        games = resp.json()
        self.assertIn(game["id"], list(map(lambda g: g["id"], games)))

    def test_game_info_invalid_id(self):
        """Invalid game ID returns 400"""
        client = get_client()
        resp = client.get(
            "/info/not-an-id",
            headers={"authorization": f"Bearer {DEFAULT_ID}"},
        )
        self.assertEqual(400, resp.status_code)

    def test_game_info(self):
        """Can retrieve information about a game"""
        client = get_client()
        original_game = completed_game()

        # get that game's info
        resp = client.get(
            f"/info/{original_game['id']}",
            headers={"authorization": f"Bearer {DEFAULT_ID}"},
        )
        game = resp.json()
        self.assertEqual(game["id"], original_game["id"])

    def test_game_players(self):
        """Can retrieve user information for players in a game"""
        client = get_client()
        original_game = completed_game()

        # Create user records for the human player (organizer)
        organizer_id = original_game["organizer"]["identifier"]
        organizer = create_user(organizer_id)

        # get that game's players
        resp = client.get(
            f"/players/game/{original_game['id']}",
            headers={"authorization": f"Bearer {DEFAULT_ID}"},
        )
        retrieved_users = resp.json()

        # Should have at least the organizer (CPU players may not have user records)
        retrieved_user_ids = list(map(lambda u: u["identifier"], retrieved_users))
        self.assertIn(organizer["identifier"], retrieved_user_ids)

    def test_lobby_players(self):
        """Can retrieve user information for players in a lobby"""
        client = get_client()
        original_lobby = lobby_game()
        other_player_ids = list(map(lambda i: f"{time()}-{i}", range(1, 4)))

        organizer = create_user(original_lobby["organizer"]["identifier"])
        other_players = list(map(create_user, other_player_ids))

        for player in other_players:
            client.post(
                f"/join/{original_lobby['id']}",
                headers={"authorization": f"Bearer {player['identifier']}"},
            )

        # get that lobby's players
        resp = client.get(
            f"/players/lobby/{original_lobby['id']}",
            headers={"authorization": f"Bearer {DEFAULT_ID}"},
        )
        retrieved_users = resp.json()

        self.assertEqual(4, len(retrieved_users))
        self.assertEqual(
            [organizer["identifier"]] + other_player_ids,
            list(map(lambda p: p["identifier"], retrieved_users)),
        )

    def test_search_users(self):
        """Can retrieve user information by substring of name"""
        client = get_client()
        # create new unique users
        timestamp = time()
        user_one = (f"{timestamp}one", f"{timestamp}aaa")
        user_two = (f"{timestamp}two", f"{timestamp}AAA")
        user_three = (f"{timestamp}three", f"{timestamp}bbb")
        create_user(user_one[0], user_one[1])
        create_user(user_two[0], user_two[1])
        create_user(user_three[0], user_three[1])

        # get users
        resp = client.get(
            "/users",
            params={"searchText": "aaa"},
            headers={"authorization": f"Bearer {DEFAULT_ID}"},
        )
        retrieved_users = resp.json()
        retrieved_user_ids = list(map(lambda u: u["identifier"], retrieved_users))
        self.assertIn(user_one[0], retrieved_user_ids)
        self.assertIn(user_two[0], retrieved_user_ids)
        self.assertNotIn(user_three[0], retrieved_user_ids)

    def test_get_suggestion_on_other_turn(self):
        """The game will not provide a suggestion on another player's turn"""
        game = started_game()
        active_player = game["round"]["active_player"]
        assert active_player
        non_active_player = next(
            p
            for p in game["round"]["players"]
            if p["identifier"] != active_player["identifier"]
        )
        resp = request_suggestion(game["id"], non_active_player["identifier"])

        self.assertEqual(400, resp.status_code)
