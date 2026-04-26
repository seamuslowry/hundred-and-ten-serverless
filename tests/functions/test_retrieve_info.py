"""Unit tests to the client can query for info as necessary"""

from time import time

from beanie import PydanticObjectId
from fastapi.testclient import TestClient

from src.models.internal import Player
from src.models.internal.constants import BidAmount, CardSuit
from tests.helpers import (
    DEFAULT_ID,
    completed_game,
    game_with_manual_player,
    get_events,
    get_game,
    lobby_game,
    player,
    queue_action,
    request_suggestions,
    started_game,
)


def test_search_winner(client: TestClient):
    """Can search by winner"""
    game = completed_game(client)
    winner_id = game["active"]["winnerPlayerId"]

    # search games
    resp = client.post(
        f"/players/{DEFAULT_ID}/games/search",
        json={"winner": winner_id},
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    )
    games = resp.json()
    assert game["id"] in list(map(lambda g: g["id"], games))


def test_search_game_smoke_test(client: TestClient):
    """Can find games by name"""
    search = f"game{time()}"
    original_games = [started_game(client, name=search) for _ in range(5)]

    p = original_games[0]["players"][0]["id"]

    resp = client.post(
        f"/players/{p}/games/search",
        json={"searchText": search},
        headers={"authorization": f"Bearer {p}"},
    )

    games = resp.json()
    assert len(original_games) == len(games)


def test_search_game_by_status(client: TestClient):
    """Can find games by status"""
    search = f"game{time()}"
    original_games = [started_game(client, name=search) for _ in range(5)]

    p = original_games[0]["players"][0]["id"]

    won_resp = client.post(
        f"/players/{p}/games/search",
        json={"activePlayer": p, "statuses": ["WON"], "searchText": search},
        headers={"authorization": f"Bearer {p}"},
    )

    won_games = won_resp.json()
    assert 0 == len(won_games)

    bidding_resp = client.post(
        f"/players/{p}/games/search",
        json={"activePlayer": p, "statuses": ["BIDDING"], "searchText": search},
        headers={"authorization": f"Bearer {p}"},
    )

    bidding_resp = bidding_resp.json()
    assert 5 == len(bidding_resp)


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
    """Can retrieve information for players in a game"""
    original_game = completed_game(client)

    # Create player records for the human player (organizer is DEFAULT_ID)
    organizer_id = DEFAULT_ID
    organizer = player(client, Player(organizer_id))

    # get that game's players
    resp = client.get(
        f"/players/{DEFAULT_ID}/games/{original_game['id']}/players",
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    )
    retrieved_players = resp.json()

    # Should have at least the organizer (CPU players may not have player records)
    retrieved_player_ids = list(map(lambda u: u["id"], retrieved_players))
    assert organizer["id"] in retrieved_player_ids


def test_lobby_players(client: TestClient):
    """Can retrieve information for players in a lobby"""
    original_lobby = lobby_game(client)
    other_player_ids = list(map(lambda i: f"{time()}-{i}", range(1, 4)))

    organizer = player(client, Player(original_lobby["organizer"]["id"]))
    other_players = list(map(lambda id: player(client, Player(id)), other_player_ids))

    for p in other_players:
        client.post(
            f"/players/{p['id']}/lobbies/{original_lobby['id']}/players",
            json={"type": "JOIN"},
            headers={"authorization": f"Bearer {p['id']}"},
        )

    # get that lobby's players
    resp = client.get(
        f"/players/{DEFAULT_ID}/lobbies/{original_lobby['id']}/players",
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    )
    retrieved_players = resp.json()

    assert 4 == len(retrieved_players)
    assert ([organizer["id"]] + other_player_ids) == list(
        map(lambda p: p["id"], retrieved_players)
    )


def test_search_players(client: TestClient):
    """Can retrieve player information by substring of name"""
    # create new unique players
    timestamp = time()
    player_one = Player(f"{timestamp}one", f"{timestamp}aaa")
    player_two = Player(f"{timestamp}two", f"{timestamp}AAA")
    player_three = Player(f"{timestamp}three", f"{timestamp}bbb")
    player(client, player_one)
    player(client, player_two)
    player(client, player_three)

    # get players
    resp = client.post(
        f"/players/{DEFAULT_ID}/search",
        json={"searchText": "aaa"},
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    )
    retrieved_players = resp.json()
    retrieved_player_ids = list(map(lambda u: u["id"], retrieved_players))
    assert player_one.player_id in retrieved_player_ids
    assert player_two.player_id in retrieved_player_ids
    assert player_three.player_id not in retrieved_player_ids


def test_get_player(client: TestClient):
    """Can retrieve player information"""
    # create new unique player
    p = player(client, Player(f"{time()}retrieve", f"{time()}retrieve"))

    # get player
    resp = client.get(
        f"/players/{p['id']}",
        headers={"authorization": f"Bearer {p['id']}"},
    )
    retrieved_player = resp.json()
    assert retrieved_player["id"] == p["id"]


def test_get_nonexistent_player(client: TestClient):
    """404s on not found player"""
    # get players
    resp = client.get(
        "/players/nonsense",
        headers={"authorization": "Bearer nonsense"},
    )
    assert 404 == resp.status_code


def test_get_suggestion_on_other_turn_no_moves(client: TestClient):
    """The game will provide a suggestion on another player's turn"""
    game, manual_player = game_with_manual_player(client)

    queue_action(
        client,
        game["id"],
        manual_player,
        {"amount": BidAmount.PASS, "type": "BID"},
    )

    # player immediately passes; play moves to DEFAULT_ID
    # manual player has no moves until the next phase, so no suggestions should be provided
    resp = request_suggestions(client, game["id"], manual_player)

    assert 200 == resp.status_code
    assert len(resp.json()) == 0


def test_get_suggestion_on_other_turn_possible_moves(client: TestClient):
    """The game will provide a suggestion on another player's turn"""
    game, manual_player = game_with_manual_player(client)

    queue_action(
        client,
        game["id"],
        manual_player,
        {"amount": BidAmount.FIFTEEN, "type": "BID"},
    )

    # player immediately bids; play moves to DEFAULT_ID
    # manual player still has possible moves in this phase so suggestions should be provided
    resp = request_suggestions(client, game["id"], manual_player)

    assert 200 == resp.status_code
    assert len(resp.json()) > 0


def test_get_all_events(client: TestClient):
    """The game will provide all events"""
    game = completed_game(client)

    events = get_events(client, game["id"], DEFAULT_ID)

    assert events[0]["type"] == "GAME_START"
    assert events[0]["sequence"] == 0
    assert events[-1]["type"] == "GAME_END"
    assert events[-1]["sequence"] == len(events) - 1


def test_get_some_events(client: TestClient):
    """The game will provide some events"""
    game = completed_game(client)

    events = client.get(
        f"/players/{DEFAULT_ID}/games/{game['id']}/events",
        params={"skip": 20, "limit": 20},
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    ).json()

    assert events[0]["sequence"] == 20
    assert events[-1]["sequence"] == 39


# ---------------------------------------------------------------------------
# New game
# ---------------------------------------------------------------------------


def test_new_game_single_active_bidding_round(client: TestClient):
    """New game has no completed rounds and an active BIDDING round."""
    game = started_game(client)
    spike = get_game(client, game["id"], DEFAULT_ID)

    assert spike["active"]["status"] == "BIDDING"
    assert spike["completedRounds"] == []
    active = spike["active"]
    assert active["trump"] is None
    assert active["tricks"] == []
    assert active["discards"] == {}


# ---------------------------------------------------------------------------
# Completed game
# ---------------------------------------------------------------------------


def test_completed_game_top_level_fields(client: TestClient):
    """Completed game has active.status WON and a winner_player_id."""
    game = completed_game(client)
    spike = get_game(client, game["id"], DEFAULT_ID)

    assert spike["active"]["status"] == "WON"
    assert spike["active"]["winnerPlayerId"] is not None
    assert spike["id"] == game["id"]
    assert spike["name"] == game["name"]
    assert len(spike["players"]) == 4
    assert isinstance(spike["scores"], dict)


def test_completed_game_all_rounds_have_status(client: TestClient):
    """All completed_rounds in a finished game are COMPLETED or COMPLETED_NO_BIDDERS."""
    game = completed_game(client)
    spike = get_game(client, game["id"], DEFAULT_ID)

    for game_round in spike["completedRounds"]:
        assert game_round["status"] in (
            "COMPLETED",
            "COMPLETED_NO_BIDDERS",
        ), f"Unexpected round status: {game_round['status']}"


def test_completed_rounds_show_full_info(client: TestClient):
    """Completed rounds shows full info."""
    game = completed_game(client)
    spike = get_game(client, game["id"], DEFAULT_ID)

    for game_round in spike["completedRounds"]:
        assert len(game_round["initialHands"].keys()) == 4
        for player_id, hand in game_round["initialHands"].items():
            assert isinstance(
                hand, list
            ), f"Player {player_id} hand should be a card list in completed round"
            assert len(hand) == 5
        if game_round["status"] == "COMPLETED":
            for player_id, discards in game_round["discards"].items():
                assert isinstance(
                    discards["discarded"], list
                ), f"Player {player_id} should show discards in a completed round"
                assert isinstance(
                    discards["received"], list
                ), f"Player {player_id} should show received cards in completed round"

                assert len(discards["discarded"]) == len(discards["received"])


def test_completed_rounds_show_tricks_with_bleeding(client: TestClient):
    """Completed rounds include trick information."""
    game = completed_game(client)
    spike = get_game(client, game["id"], DEFAULT_ID)

    for game_round in spike["completedRounds"]:
        if game_round["status"] == "COMPLETED":
            assert len(game_round["tricks"]) == 5
            for trick in game_round["tricks"]:
                assert "bleeding" in trick
                assert isinstance(trick["bleeding"], bool)
                assert trick["winningPlay"] is not None


def test_all_pass_rounds_have_hands_but_no_tricks(client: TestClient):
    """COMPLETED_NO_BIDDERS rounds have initial_hands but no tricks or discards."""

    no_bidders_rounds = []

    # be sure that the game has COMPLETED_NO_BIDDERS to avoid flake
    while not no_bidders_rounds:
        game = completed_game(client)
        spike = get_game(client, game["id"], DEFAULT_ID)

        no_bidders_rounds = [
            r for r in spike["completedRounds"] if r["status"] == "COMPLETED_NO_BIDDERS"
        ]

    for game_round in no_bidders_rounds:
        assert len(game_round["initialHands"]) == 4
        # COMPLETED_NO_BIDDERS rounds only have: status, dealer_player_id, initial_hands
        assert set(game_round.keys()) == {
            "status",
            "dealerPlayerId",
            "initialHands",
        }
        break


def test_completed_game_scores_sum_to_cumulative(client: TestClient):
    """Sum of COMPLETED round scores equals top-level cumulative scores.
    COMPLETED_NO_BIDDERS rounds score 0 for all players and have no scores field.
    """
    game = completed_game(client)
    spike = get_game(client, game["id"], DEFAULT_ID)

    total: dict[str, int] = {}
    for game_round in spike["completedRounds"]:
        if game_round["status"] == "COMPLETED":
            for pid, v in game_round["scores"].items():
                total[pid] = total.get(pid, 0) + v

    for pid, expected in spike["scores"].items():
        assert (
            total.get(pid, 0) == expected
        ), f"Player {pid}: round score sum {total.get(pid, 0)} != cumulative {expected}"


# ---------------------------------------------------------------------------
# Completed game: de-anonymization is requester-independent
# ---------------------------------------------------------------------------


def test_two_players_see_identical_completed_round_data(client: TestClient):
    """Two different players see the same data for completed rounds."""
    game = completed_game(client)
    # The active_player_id before the game ended is stored in the game
    # Use two player IDs from the game's players list
    player_ids = [p["id"] for p in game["players"]]
    p1, p2 = player_ids[0], player_ids[1]

    spike_p1 = get_game(client, game["id"], p1)
    spike_p2 = get_game(client, game["id"], p2)

    assert spike_p1 == spike_p2


# ---------------------------------------------------------------------------
# Active round
# ---------------------------------------------------------------------------


def test_new_trick_no_winning_play(client: TestClient):
    """A trick with only has a winning play with >0 plays."""
    game, manual_player = game_with_manual_player(client)

    queue_action(
        client,
        game["id"],
        DEFAULT_ID,
        {"type": "BID", "amount": BidAmount.SHOOT_THE_MOON},
    )
    queue_action(
        client,
        game["id"],
        DEFAULT_ID,
        {"type": "SELECT_TRUMP", "suit": CardSuit.DIAMONDS},
    )
    queue_action(client, game["id"], DEFAULT_ID, {"type": "DISCARD", "cards": []})
    queue_action(
        client, game["id"], manual_player, {"type": "BID", "amount": BidAmount.PASS}
    )
    queue_action(client, game["id"], manual_player, {"type": "DISCARD", "cards": []})

    no_plays = get_game(client, game["id"], manual_player)
    no_plays_round = no_plays["active"]
    assert no_plays_round["status"] == "TRICKS"
    assert len(no_plays_round["tricks"]) == 1
    assert len(no_plays_round["tricks"][0]["plays"]) == 0
    assert no_plays_round["tricks"][0]["winningPlay"] is None

    queue_action(
        client,
        game["id"],
        manual_player,
        {"type": "PLAY", "card": no_plays["active"]["hands"][manual_player][0]},
    )

    one_play = get_game(client, game["id"], manual_player)
    one_play_round = one_play["active"]
    assert one_play_round["status"] == "TRICKS"
    assert len(one_play_round["tricks"]) == 1
    assert len(one_play_round["tricks"][0]["plays"]) == 3  # manual and two automatic
    assert one_play_round["tricks"][0]["winningPlay"] is not None


def test_active_round_matching_bid_shows_latest(client: TestClient):
    """Active round shows the latest bid of matching values."""
    game, manual_player = game_with_manual_player(client)

    queue_action(
        client,
        game["id"],
        manual_player,
        {"type": "BID", "amount": BidAmount.SHOOT_THE_MOON},
    )
    queue_action(
        client,
        game["id"],
        DEFAULT_ID,
        {"type": "BID", "amount": BidAmount.SHOOT_THE_MOON},
    )

    spike = get_game(client, game["id"], DEFAULT_ID)

    active = spike["active"]

    assert active["bid"]["playerId"] == DEFAULT_ID


def test_active_round_self_sees_cards(client: TestClient):
    """Requesting player sees only their own hand as cards."""
    game = started_game(client)
    spike = get_game(client, game["id"], DEFAULT_ID)

    active = spike["active"]
    assert active["status"] == "BIDDING"
    assert isinstance(active["hands"][DEFAULT_ID], list)
    assert len(active["hands"][DEFAULT_ID]) == 5
    for card in active["hands"][DEFAULT_ID]:
        assert "suit" in card
        assert "number" in card


def test_active_round_others_see_count(client: TestClient):
    """Other players' hands are integers in the active round."""
    game = started_game(client)
    spike = get_game(client, game["id"], DEFAULT_ID)

    active = spike["active"]
    for pid, hand in active["hands"].items():
        if pid != DEFAULT_ID:
            assert isinstance(hand, int)
            assert hand == 5


def test_active_round_includes_active_player_id(client: TestClient):
    """Active round includes active_player_id."""
    game = started_game(client)
    spike = get_game(client, game["id"], DEFAULT_ID)

    active = spike["active"]
    assert "activePlayerId" in active
    assert active["activePlayerId"] == game["active"]["activePlayerId"]


def test_two_players_see_different_hands_in_active_round(client: TestClient):
    """Two players see each other's hands as counts."""
    game, manual_player = game_with_manual_player(client)

    spike_organizer = get_game(client, game["id"], DEFAULT_ID)
    spike_manual = get_game(client, game["id"], manual_player)

    active_org = spike_organizer["active"]
    active_man = spike_manual["active"]

    # Organizer sees own cards, manual player as count
    assert isinstance(active_org["hands"][DEFAULT_ID], list)
    assert isinstance(active_org["hands"][manual_player], int)

    # Manual player sees own cards, organizer as count
    assert isinstance(active_man["hands"][manual_player], list)
    assert isinstance(active_man["hands"][DEFAULT_ID], int)


def test_active_round_bid_is_none_before_any_bid(client: TestClient):
    """Active round bid field is null when no one has bid yet.

    Uses game_with_manual_player so the first active player is Human and no
    CPU automation fires before the first act, guaranteeing bid starts null.
    """
    game, _ = game_with_manual_player(client)
    spike = get_game(client, game["id"], DEFAULT_ID)

    assert spike["active"]["bid"] is None


def test_active_round_bid_populated_after_a_bid(client: TestClient):
    """Active round bid field contains player_id and amount once a bid is placed."""
    game, manual_player = game_with_manual_player(client)
    assert game["active"]["activePlayerId"] == manual_player

    queue_action(
        client, game["id"], manual_player, {"type": "BID", "amount": BidAmount.TWENTY}
    )

    spike = get_game(client, game["id"], DEFAULT_ID)
    bid = spike["active"]["bid"]
    assert bid is not None

    assert {
        "type": "BID",
        "playerId": manual_player,
        "amount": BidAmount.TWENTY,
    } in spike["active"]["bidHistory"]


def test_active_round_queued_actions(client: TestClient):
    """Active round includes queued_actions field for the requesting player."""
    game, _ = game_with_manual_player(client)

    # Queue an action for DEFAULT_ID (organizer) when it may not be their turn
    queue_action(
        client,
        game["id"],
        DEFAULT_ID,
        {"amount": BidAmount.TWENTY, "type": "BID"},
    )

    spike = get_game(client, game["id"], DEFAULT_ID)
    active = spike["active"]
    assert "queuedActions" in active
    # queuedActions may be empty if action was consumed; field presence is what matters
    assert isinstance(active["queuedActions"], list)


# ---------------------------------------------------------------------------
# Error path
# ---------------------------------------------------------------------------


def test_nonexistent_game_returns_404(client: TestClient):
    """Error path: non-existent game ID returns 404."""
    resp = client.get(
        f"/players/{DEFAULT_ID}/games/000000000000000000000000/spike",
        headers={"authorization": f"Bearer {DEFAULT_ID}"},
    )
    assert resp.status_code == 404
