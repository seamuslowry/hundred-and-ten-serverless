"""Ensure edge cases of mapping are unit tested"""

import pytest

from src.main.mappers.db import serialize as db_serialize
from src.main.models.internal import (
    Accessibility,
    Lobby,
    PlayerGroup,
    PlayerInGame,
)


def test_unknown_internal_person_type_error():
    """Raises an error trying to serialize an unknown person type"""

    class UnknownPerson(PlayerInGame):
        """A subclassed person type the serializer is unaware of"""

        def queue_action(self, action):
            raise NotImplementedError()

        def clear_queued_actions(self):
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
