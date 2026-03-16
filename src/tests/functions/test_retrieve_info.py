"""Unit tests to the client can query for info as necessary"""

from time import time

from beanie import PydanticObjectId
from fastapi.testclient import TestClient

from src.main.models.internal import Player
from src.tests.helpers import (
    DEFAULT_ID,
    completed_game,
    lobby_game,
    request_suggestion,
    started_game,
    user,
)


def test_search_winner(client: TestClient):
    """Can search by winner"""
    game = completed_game(client)

    # search games
    resp = client.post(
        f"/players/{DEFAULT_ID}/games/search",
        json={"winner": game["winner"]["id"]},
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    )
    games = resp.json()
    assert game["id"] in list(map(lambda g: g["id"], games))


def test_search_game_smoke_test(client: TestClient):
    """Can find games by name"""
    search = f"game{time()}"
    original_games = [started_game(client, name=search) for _ in range(5)]

    player = original_games[0]["players"][0]["id"]

    resp = client.post(
        f"/players/{player}/games/search",
        json={"searchText": search},
        headers={"authorization": f"Bearer {player}"},
    )

    games = resp.json()
    assert len(original_games) == len(games)


def test_search_game_by_status(client: TestClient):
    """Can find games by status"""
    search = f"game{time()}"
    original_games = [started_game(client, name=search) for _ in range(5)]

    player = original_games[0]["players"][0]["id"]

    won_resp = client.post(
        f"/players/{player}/games/search",
        json={"activePlayer": player, "statuses": ["WON"]},
        headers={"authorization": f"Bearer {player}"},
    )

    won_games = won_resp.json()
    assert 0 == len(won_games)

    bidding_resp = client.post(
        f"/players/{player}/games/search",
        json={"activePlayer": player, "statuses": ["BIDDING"]},
        headers={"authorization": f"Bearer {player}"},
    )

    bidding_resp = won_resp.json()
    assert 0 == len(bidding_resp)


def test_search_game_by_active_player(client: TestClient):
    """Can find games by active player"""
    search = f"game{time()}"
    active_player = f"player{time()}"
    original_games = [
        started_game(client, organizer=active_player, name=search) for _ in range(5)
    ]

    resp = client.post(
        f"/players/{active_player}/games/search",
        json={"activePlayer": active_player},
        headers={"authorization": f"Bearer {active_player}"},
    )

    games = resp.json()
    assert len(original_games) == len(games)


def test_game_info_invalid_id(client: TestClient):
    """Invalid game ID returns 422"""
    resp = client.get(
        f"/players/{DEFAULT_ID}/games/not-an-id",
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    )
    assert 422 == resp.status_code


def test_game_info_id_doesnt_exist(client: TestClient):
    """Invalid game ID returns 404"""
    resp = client.get(
        f"/players/{DEFAULT_ID}/games/{PydanticObjectId()}",
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    )
    assert 404 == resp.status_code


def test_game_info(client: TestClient):
    """Can retrieve information about a game"""
    original_game = completed_game(client)

    # get that game's info
    resp = client.get(
        f"/players/{DEFAULT_ID}/games/{original_game['id']}",
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    )
    game = resp.json()
    assert game["id"] == original_game["id"]


def test_game_players(client: TestClient):
    """Can retrieve user information for players in a game"""
    original_game = completed_game(client)

    # Create user records for the human player (organizer)
    organizer_id = original_game["organizer"]["id"]
    organizer = user(client, Player(organizer_id))

    # get that game's players
    resp = client.get(
        f"/players/{DEFAULT_ID}/games/{original_game['id']}/players",
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    )
    retrieved_users = resp.json()

    # Should have at least the organizer (CPU players may not have user records)
    retrieved_user_ids = list(map(lambda u: u["id"], retrieved_users))
    assert organizer["id"] in retrieved_user_ids


def test_lobby_players(client: TestClient):
    """Can retrieve user information for players in a lobby"""
    original_lobby = lobby_game(client)
    other_player_ids = list(map(lambda i: f"{time()}-{i}", range(1, 4)))

    organizer = user(client, Player(original_lobby["organizer"]["id"]))
    other_players = list(map(lambda id: user(client, Player(id)), other_player_ids))

    for player in other_players:
        client.post(
            f"/players/{player['id']}/lobbies/{original_lobby['id']}/join",
            headers={"authorization": f"Bearer {player['id']}"},
        )

    # get that lobby's players
    resp = client.get(
        f"/players/{DEFAULT_ID}/lobbies/{original_lobby['id']}/players",
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    )
    retrieved_users = resp.json()

    assert 4 == len(retrieved_users)
    assert ([organizer["id"]] + other_player_ids) == list(
        map(lambda p: p["id"], retrieved_users)
    )


def test_search_users(client: TestClient):
    """Can retrieve user information by substring of name"""
    # create new unique users
    timestamp = time()
    user_one = Player(f"{timestamp}one", f"{timestamp}aaa")
    user_two = Player(f"{timestamp}two", f"{timestamp}AAA")
    user_three = Player(f"{timestamp}three", f"{timestamp}bbb")
    user(client, user_one)
    user(client, user_two)
    user(client, user_three)

    # get users
    resp = client.get(
        f"/players/{DEFAULT_ID}/search",
        params={"searchText": "aaa"},
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    )
    retrieved_users = resp.json()
    retrieved_user_ids = list(map(lambda u: u["id"], retrieved_users))
    assert user_one.player_id in retrieved_user_ids
    assert user_two.player_id in retrieved_user_ids
    assert user_three.player_id not in retrieved_user_ids


def test_get_suggestion_on_other_turn(client: TestClient):
    """The game will provide a suggestion on another player's turn"""
    game = started_game(client)
    active_player = game["round"]["active_player"]
    assert active_player
    non_active_player = next(
        p for p in game["round"]["players"] if p["id"] != active_player["id"]
    )
    resp = request_suggestion(client, game["id"], non_active_player["id"])

    assert 200 == resp.status_code
