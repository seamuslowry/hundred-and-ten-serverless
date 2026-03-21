"""Ensure edge cases of mapping are unit tested"""

import pytest
from hundredandten.events import Event

from src.main.mappers.client import deserialize as client_deserialize
from src.main.mappers.client import serialize as client_serialize
from src.main.mappers.db import serialize as db_serialize
from src.main.models.client.constants import CardNumberName, Suit
from src.main.models.client.requests import CardRequest, PlayRequest
from src.main.models.internal import (
    Accessibility,
    Action,
    Card,
    CardNumber,
    Lobby,
    Play,
    PlayerGroup,
    PlayerInGame,
    UnselectableSuit,
)


def test_bad_suggestion_error():
    """Attempting to serialize an invalid suggestion results in an error"""
    player_id = "player_id"
    with pytest.raises(ValueError):
        client_serialize.action(Action(player_id))


def test_card_with_unselectable_suit():
    """Deserializing a card with an UnselectableSuit should succeed"""
    result = client_deserialize.action(
        "playerid",
        PlayRequest(
            type="PLAY", card=CardRequest(suit=Suit.JOKER, number=CardNumberName.JOKER)
        ),
    )
    assert isinstance(result, Play) and result.card == Card(
        suit=UnselectableSuit.JOKER, number=CardNumber.JOKER
    )


def test_unknown_event_type_error():
    """Serializing an unknown event type raises ValueError"""
    with pytest.raises(ValueError):
        client_serialize.events([Event()], "player_id")


def test_unknown_internal_person_type_error():
    """Raises an error trying to serialize an unknown person type"""

    class UnknownPerson(PlayerInGame):
        """A subclassed person type the serializer is unaware of"""

        def queue_action(self, action):
            raise NotImplementedError()

        def as_engine_player(self):
            raise NotImplementedError()

    with pytest.raises(ValueError):
        db_serialize.lobby(
            Lobby(
                name="",
                accessibility=Accessibility.PUBLIC,
                organizer=UnknownPerson(""),
                players=PlayerGroup([]),
                invitees=PlayerGroup([]),
            )
        )
