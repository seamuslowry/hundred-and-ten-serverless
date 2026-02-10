"""Ensure edge cases of mapping are unit tested"""

from unittest import TestCase

import azure.functions as func

from utils.dtos.db import Game as DbGame
from utils.dtos.db import Person as DbPerson
from utils.mappers.client import deserialize as client_deserialize
from utils.mappers.client import serialize as client_serialize
from utils.mappers.db import deserialize as db_deserialize
from utils.models import Action


class TestMapperEdgeCases(TestCase):
    """Unit tests to ensure mapper edge cases behave as expected"""

    def test_bad_suggestion_error(self):
        """Attempting to serialize an invalid suggestion results in an error"""
        identifier = "identifier"
        self.assertRaises(
            ValueError, client_serialize.suggestion, Action(identifier), identifier
        )

    def test_incomplete_user_info(self):
        """Attempting to serialize a user with incomplete header info results in an error"""
        self.assertRaises(
            ValueError,
            client_deserialize.user_id,
            func.HttpRequest(method="GET", body=b"", url="", headers={}),
        )

    def test_bad_action_from_db(self):
        """Attempting to deserialize an invalid action from DB results in an error"""
        identifier = "identifier"
        self.assertRaises(
            ValueError,
            db_deserialize.game,
            DbGame(
                type="game",
                id="test",
                name="test",
                seed="test",
                accessibility="PUBLIC",
                organizer=DbPerson(identifier="dummy", automate=False),
                players=[],
                # ignoring type because this wants to test bad value
                moves=[{"identifier": identifier, "type": "unknown"}],  # type: ignore
                status="PLAYING",
                winner=None,
                active_player=None,
            ),
        )
