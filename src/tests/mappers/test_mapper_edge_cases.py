"""Ensure edge cases of mapping are unit tested"""

from unittest import TestCase

from hundredandten.events import Event
from hundredandten.player import HumanPlayer

from src.main.mappers.client import deserialize as client_deserialize
from src.main.mappers.client import serialize as client_serialize
from src.main.mappers.db import deserialize as db_deserialize
from src.main.mappers.db import serialize as db_serialize
from src.main.models.client.constants import CardNumberName, Suit
from src.main.models.client.requests import CardRequest
from src.main.models.internal import Action, Card, CardNumber, Person, UnselectableSuit


def _raise_unknown_db_player_type() -> None:
    getattr(db_deserialize, "__person")(object())


def _raise_unknown_db_move_type() -> None:
    unknown_move = type("UnknownMove", (), {"type": "unknown", "identifier": "id"})()
    getattr(db_deserialize, "__move")(unknown_move)


def _raise_unknown_internal_person_type() -> None:
    class _UnknownPerson(Person):
        def as_player(self):
            return HumanPlayer(self.identifier)

    getattr(db_serialize, "__person")(_UnknownPerson("id"))


class TestMapperEdgeCases(TestCase):
    """Unit tests to ensure mapper edge cases behave as expected"""

    def test_bad_suggestion_error(self):
        """Attempting to serialize an invalid suggestion results in an error"""
        identifier = "identifier"
        self.assertRaises(ValueError, client_serialize.suggestion, Action(identifier))

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

    def test_unknown_db_player_type_error(self):
        self.assertRaises(ValueError, _raise_unknown_db_player_type)

    def test_unknown_db_move_type_error(self):
        self.assertRaises(ValueError, _raise_unknown_db_move_type)

    def test_unknown_internal_person_type_error(self):
        self.assertRaises(ValueError, _raise_unknown_internal_person_type)
