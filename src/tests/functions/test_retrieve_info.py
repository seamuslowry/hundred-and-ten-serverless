"""Retrieve Info unit tests"""

from time import time

from fastapi.testclient import TestClient

from src.tests.helpers import (
    DEFAULT_ID,
    completed_game,
    create_user,
    lobby_game,
    request_suggestion,
    started_game,
)


class TestRetrieveInfo:
    """Unit tests to the client can query for info as necessary"""

    def test_search_winner(self, client: TestClient):
        """Can search by winner"""
        game = completed_game(client)

        # search games
        resp = client.post(
            f"/players/{DEFAULT_ID}/games/search",
            json={"winner": game["winner"]["identifier"]},
            headers={"authorization": f"Bearer {DEFAULT_ID}"},
        )
        games = resp.json()
        assert game["id"] in list(map(lambda g: g["id"], games))

    def test_game_info_invalid_id(self, client: TestClient):
        """Invalid game ID returns 400"""
        resp = client.get(
            f"/players/{DEFAULT_ID}/games/not-an-id",
            headers={"authorization": f"Bearer {DEFAULT_ID}"},
        )
        assert 400 == resp.status_code

    def test_game_info(self, client: TestClient):
        """Can retrieve information about a game"""
        original_game = completed_game(client)

        # get that game's info
        resp = client.get(
            f"/players/{DEFAULT_ID}/games/{original_game['id']}",
            headers={"authorization": f"Bearer {DEFAULT_ID}"},
        )
        game = resp.json()
        assert game["id"] == original_game["id"]

    def test_game_players(self, client: TestClient):
        """Can retrieve user information for players in a game"""
        original_game = completed_game(client)

        # Create user records for the human player (organizer)
        organizer_id = original_game["organizer"]["identifier"]
        organizer = create_user(client, organizer_id)

        # get that game's players
        resp = client.get(
            f"/players/{DEFAULT_ID}/games/{original_game['id']}/players",
            headers={"authorization": f"Bearer {DEFAULT_ID}"},
        )
        retrieved_users = resp.json()

        # Should have at least the organizer (CPU players may not have user records)
        retrieved_user_ids = list(map(lambda u: u["identifier"], retrieved_users))
        assert organizer["identifier"] in retrieved_user_ids

    def test_lobby_players(self, client: TestClient):
        """Can retrieve user information for players in a lobby"""
        original_lobby = lobby_game(client)
        other_player_ids = list(map(lambda i: f"{time()}-{i}", range(1, 4)))

        organizer = create_user(client, original_lobby["organizer"]["identifier"])
        other_players = list(map(lambda id: create_user(client, id), other_player_ids))

        for player in other_players:
            client.post(
                f"/players/{player['identifier']}/lobbies/{original_lobby['id']}/join",
                headers={"authorization": f"Bearer {player['identifier']}"},
            )

        # get that lobby's players
        resp = client.get(
            f"/players/{DEFAULT_ID}/lobbies/{original_lobby['id']}/players",
            headers={"authorization": f"Bearer {DEFAULT_ID}"},
        )
        retrieved_users = resp.json()

        assert 4 == len(retrieved_users)
        assert ([organizer["identifier"]] + other_player_ids) == list(
            map(lambda p: p["identifier"], retrieved_users)
        )

    def test_search_users(self, client: TestClient):
        """Can retrieve user information by substring of name"""
        # create new unique users
        timestamp = time()
        user_one = (f"{timestamp}one", f"{timestamp}aaa")
        user_two = (f"{timestamp}two", f"{timestamp}AAA")
        user_three = (f"{timestamp}three", f"{timestamp}bbb")
        create_user(client, user_one[0], user_one[1])
        create_user(client, user_two[0], user_two[1])
        create_user(client, user_three[0], user_three[1])

        # get users
        resp = client.get(
            f"/players/{DEFAULT_ID}/search",
            params={"searchText": "aaa"},
            headers={"authorization": f"Bearer {DEFAULT_ID}"},
        )
        retrieved_users = resp.json()
        retrieved_user_ids = list(map(lambda u: u["identifier"], retrieved_users))
        assert user_one[0] in retrieved_user_ids
        assert user_two[0] in retrieved_user_ids
        assert user_three[0] not in retrieved_user_ids

    def test_get_suggestion_on_other_turn(self, client: TestClient):
        """The game will provide a suggestion on another player's turn"""
        game = started_game(client)
        active_player = game["round"]["active_player"]
        assert active_player
        non_active_player = next(
            p
            for p in game["round"]["players"]
            if p["identifier"] != active_player["identifier"]
        )
        resp = request_suggestion(client, game["id"], non_active_player["identifier"])

        assert 200 == resp.status_code
