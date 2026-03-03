"""Playing Game unit tests"""

from unittest import TestCase

from tests.helpers import (
    DEFAULT_ID,
    get_client,
    get_suggestion,
    started_game,
)
from utils.models import BidAmount, RoundStatus, SelectableSuit


class TestPlayingGame(TestCase):
    """Unit tests to ensure games that are in progress behave as expected"""

    def test_perform_round_actions(self):
        """A round of the game can be played"""
        client = get_client()
        created_game = started_game()
        self.assertEqual(RoundStatus.BIDDING.name, created_game["status"])

        # assert that current suggestion is a bid
        suggested_bid = get_suggestion(created_game["id"])
        assert "amount" in suggested_bid

        # bid
        resp = client.post(
            f"/bid/{created_game['id']}",
            json={"amount": BidAmount.SHOOT_THE_MOON},
            headers={"authorization": f"Bearer {DEFAULT_ID}"},
        )
        game = resp.json()

        self.assertEqual(RoundStatus.TRUMP_SELECTION.name, game["status"])

        # assert that current suggestion is a trump selection
        suggested_trump = get_suggestion(created_game["id"])
        assert "suit" in suggested_trump

        # select trump
        resp = client.post(
            f"/select/{created_game['id']}",
            json={"suit": SelectableSuit.CLUBS.name},
            headers={"authorization": f"Bearer {DEFAULT_ID}"},
        )
        game = resp.json()

        print(game)

        self.assertEqual(RoundStatus.DISCARD.name, game["status"])

        # assert that current suggestion is a discard
        suggested_discard = get_suggestion(created_game["id"])
        assert "cards" in suggested_discard

        # discard
        resp = client.post(
            f"/discard/{created_game['id']}",
            json={"cards": []},
            headers={"authorization": f"Bearer {DEFAULT_ID}"},
        )
        game = resp.json()

        self.assertEqual(RoundStatus.TRICKS.name, game["status"])

        # ask for a suggestion so we know what card we can play
        suggested_play = get_suggestion(created_game["id"])
        assert "card" in suggested_play

        # play
        resp = client.post(
            f"/play/{created_game['id']}",
            json={"card": suggested_play["card"]},  # type: ignore
            headers={"authorization": f"Bearer {DEFAULT_ID}"},
        )
        game = resp.json()

        self.assertEqual(RoundStatus.TRICKS.name, game["status"])
        self.assertEqual(2, len(game["round"]["tricks"]))

    def test_prepass_and_rescind_prepass(self):
        """A non-active player can prepass and rescind that prepass"""
        client = get_client()
        game = started_game()

        non_active_player = next(
            p
            for p in game["round"]["players"]
            if game["round"]["active_player"]
            and p["identifier"] != game["round"]["active_player"]["identifier"]
        )

        # prepass
        resp = client.post(
            f"/bid/{game['id']}",
            json={"amount": BidAmount.PASS},
            headers={"authorization": f"Bearer {non_active_player['identifier']}"},
        )
        game = resp.json()
        non_active_player = next(
            p
            for p in game["round"]["players"]
            if p["identifier"] == non_active_player["identifier"]
        )
        self.assertTrue(
            "prepassed" in non_active_player and non_active_player["prepassed"]
        )

        # rescind prepass
        resp = client.post(
            f"/unpass/{game['id']}",
            headers={"authorization": f"Bearer {non_active_player['identifier']}"},
        )
        game = resp.json()
        non_active_player = next(
            p
            for p in game["round"]["players"]
            if p["identifier"] == non_active_player["identifier"]
        )
        self.assertTrue("prepassed" in non_active_player)
        self.assertFalse(
            "prepassed" in non_active_player and non_active_player["prepassed"]
        )

    def test_leave_playing_game(self):
        """A player can leave an active game by automating themselves"""
        client = get_client()
        original_game = started_game()
        active_player = original_game["round"]["active_player"]
        assert active_player
        self.assertFalse(active_player["automate"])

        # leave
        resp = client.post(
            f"/leave/game/{original_game['id']}",
            headers={"authorization": f"Bearer {active_player['identifier']}"},
        )
        game = resp.json()
        active_player = next(
            p for p in game["players"] if p["identifier"] == active_player["identifier"]
        )

        self.assertTrue(active_player["automate"])
