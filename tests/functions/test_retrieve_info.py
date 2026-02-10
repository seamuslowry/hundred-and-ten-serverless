"""Retrieve Info unit tests"""

from time import time
from unittest import TestCase

from function_app import (
    game_info as wrapped_game_info,
)
from function_app import (
    game_players as wrapped_game_players,
)
from function_app import (
    join_lobby as wrapped_join_lobby,
)
from function_app import (
    lobby_players as wrapped_lobby_players,
)
from function_app import (
    search_games as wrapped_search_games,
)
from function_app import (
    search_users as wrapped_search_users,
)
from tests.helpers import (
    build_request,
    completed_game,
    create_user,
    lobby_game,
    read_response_body,
    request_suggestion,
    started_game,
)
from utils.dtos.client import CompletedGame, User, WaitingGame

game_info = wrapped_game_info.build().get_user_function()
game_players = wrapped_game_players.build().get_user_function()
join_lobby = wrapped_join_lobby.build().get_user_function()
lobby_players = wrapped_lobby_players.build().get_user_function()
search_games = wrapped_search_games.build().get_user_function()
search_users = wrapped_search_users.build().get_user_function()


class TestRetrieveInfo(TestCase):
    """Unit tests to the client can query for info as necessary"""

    def test_search_winner(self):
        """Can search by winner"""
        game: CompletedGame = completed_game()

        # search games
        resp = search_games(
            build_request(body={"winner": game["winner"]["identifier"]})
        )
        games = read_response_body(resp.get_body())
        self.assertIn(game["id"], list(map(lambda g: g["id"], games)))

    def test_game_info_invalid_id(self):
        """Invalid game ID returns 400"""
        resp = game_info(build_request(route_params={"game_id": "not-an-id"}))
        self.assertEqual(400, resp.status_code)

    def test_game_info(self):
        """Can retrieve information about a game"""
        original_game: CompletedGame = completed_game()

        # get that game's info
        resp = game_info(build_request(route_params={"game_id": original_game["id"]}))
        game = read_response_body(resp.get_body())
        self.assertEqual(game["id"], original_game["id"])

    def test_game_players(self):
        """Can retrieve user information for players in a game"""
        original_game: CompletedGame = completed_game()

        # Create user records for the human player (organizer)
        organizer_id = original_game["organizer"]["identifier"]
        organizer: User = create_user(organizer_id)

        # get that game's players
        resp = game_players(
            build_request(route_params={"game_id": original_game["id"]})
        )
        retrieved_users: list[User] = read_response_body(resp.get_body())

        # Should have at least the organizer (CPU players may not have user records)
        retrieved_user_ids = list(map(lambda u: u["identifier"], retrieved_users))
        self.assertIn(organizer["identifier"], retrieved_user_ids)

    def test_lobby_players(self):
        """Can retrieve user information for players in a lobby"""
        original_lobby: WaitingGame = lobby_game()
        other_player_ids = list(map(lambda i: f"{time()}-{i}", range(1, 4)))

        organizer: User = create_user(original_lobby["organizer"]["identifier"])
        other_players: list[User] = list(map(create_user, other_player_ids))

        for player in other_players:
            join_lobby(
                build_request(
                    route_params={"lobby_id": original_lobby["id"]},
                    headers={"x-ms-client-principal-id": player["identifier"]},
                )
            )

        # get that lobby's players
        resp = lobby_players(
            build_request(route_params={"lobby_id": original_lobby["id"]})
        )
        retrieved_users: list[User] = read_response_body(resp.get_body())

        self.assertEqual(4, len(retrieved_users))
        self.assertEqual(
            [organizer["identifier"]] + other_player_ids,
            list(map(lambda p: p["identifier"], retrieved_users)),
        )

    def test_search_users(self):
        """Can retrieve user information by substring of name"""
        # create new unique users
        timestamp = time()
        user_one = (f"{timestamp}one", f"{timestamp}aaa")
        user_two = (f"{timestamp}two", f"{timestamp}AAA")
        user_three = (f"{timestamp}three", f"{timestamp}bbb")
        create_user(user_one[0], user_one[1])
        create_user(user_two[0], user_two[1])
        create_user(user_three[0], user_three[1])

        # get users
        resp = search_users(build_request(params={"searchText": "aaa"}))
        retrieved_users: list[User] = read_response_body(resp.get_body())
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
