"""Ensure edge cases of mapping are unit tested"""

import pytest
from hundredandten.events import Event

from src.main.mappers.client import deserialize as client_deserialize
from src.main.mappers.client import serialize as client_serialize
from src.main.mappers.db import serialize as db_serialize
from src.main.models.client.constants import CardNumberName, Suit
from src.main.models.client.requests import CardRequest
from src.main.models.internal import (
    Accessibility,
    Action,
    Card,
    CardNumber,
    Lobby,
    Person,
    PersonGroup,
    UnselectableSuit,
)


def test_bad_suggestion_error():
    """Attempting to serialize an invalid suggestion results in an error"""
    identifier = "identifier"
    with pytest.raises(ValueError):
        client_serialize.suggestion(Action(identifier))


def test_card_with_unselectable_suit():
    """Deserializing a card with an UnselectableSuit should succeed"""
    result = client_deserialize.card(
        CardRequest(suit=Suit.JOKER, number=CardNumberName.JOKER)
    )
    assert result == Card(suit=UnselectableSuit.JOKER, number=CardNumber.JOKER)


def test_unknown_event_type_error():
    """Serializing an unknown event type raises ValueError"""
    with pytest.raises(ValueError):
        client_serialize.events([Event()], "identifier")


def test_unknown_internal_person_type_error():
    """Raises an error trying to serialize an unknown person type"""

    class UnknownPerson(Person):
        """A subclassed person type the serializer is unaware of"""

        def as_player(self):
            raise NotImplementedError()

    with pytest.raises(ValueError):
        db_serialize.lobby(
            Lobby(
                name="",
                accessibility=Accessibility.PUBLIC,
                organizer=UnknownPerson(""),
                players=PersonGroup([]),
                invitees=PersonGroup([]),
            )
        )
