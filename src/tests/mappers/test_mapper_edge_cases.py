"""Ensure edge cases of mapping are unit tested"""

from unittest import TestCase

from hundredandten.events import Event

from src.main.mappers.client import deserialize as client_deserialize
from src.main.mappers.client import serialize as client_serialize
from src.main.mappers.db import deserialize as db_deserialize
from src.main.models.client.constants import CardNumberName, Suit
from src.main.models.client.requests import CardRequest
from src.main.models.db.db import Game as DbGame
from src.main.models.db.db import Person as DbPerson
from src.main.models.internal import Action, Card, CardNumber, UnselectableSuit


class TestMapperEdgeCases(TestCase):
    """Unit tests to ensure mapper edge cases behave as expected"""

    def test_bad_suggestion_error(self):
        """Attempting to serialize an invalid suggestion results in an error"""
        identifier = "identifier"
        self.assertRaises(ValueError, client_serialize.suggestion, Action(identifier))

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

    def test_card_with_unselectable_suit(self):
        """Deserializing a card with an UnselectableSuit should succeed"""
        result = client_deserialize.card(
            CardRequest(suit=Suit.JOKER, number=CardNumberName.JOKER)
        )
        self.assertEqual(
            result, Card(suit=UnselectableSuit.JOKER, number=CardNumber.JOKER)
        )

    def test_unknown_event_type_error(self):
        """Serializing an unknown event type raises ValueError"""
        self.assertRaises(ValueError, client_serialize.events, [Event()], "identifier")
