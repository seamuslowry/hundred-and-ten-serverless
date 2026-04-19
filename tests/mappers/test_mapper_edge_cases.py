"""Ensure edge cases of mapping are unit tested"""

import pytest

from src.mappers.client import serialize as client_serialize
from src.mappers.db import serialize as db_serialize
from src.models.internal import (
    Accessibility,
    Game,
    Lobby,
    PlayerGroup,
    PlayerInGame,
)
from src.models.internal.player import NoAction


def test_unknown_internal_person_type_error():
    """Raises an error trying to serialize an unknown person type"""

    class UnknownPerson(PlayerInGame):
        """A subclassed person type the serializer is unaware of"""

        def next_action(self):
            return NoAction()

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

    with pytest.raises(ValueError):
        client_serialize.game(
            Game(
                id="test",
                name="",
                accessibility=Accessibility.PUBLIC,
                organizer=UnknownPerson("o"),
                players=PlayerGroup([UnknownPerson("p")]),
            ),
            "o",
        )
