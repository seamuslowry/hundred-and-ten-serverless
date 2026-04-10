"""Ensure edge cases of mapping are unit tested"""

import pytest
from hundredandten.player import HumanPlayer

from src.mappers.client import serialize as client_serialize
from src.mappers.db import serialize as db_serialize
from src.models.internal import (
    Accessibility,
    Game,
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
            return HumanPlayer(self.id)

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
