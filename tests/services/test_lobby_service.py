"""Lobby Service unit tests"""

from time import time
from unittest import TestCase

from utils.dtos.db import SearchLobby
from utils.models import GameRole, Lobby, Person, PersonGroup
from utils.services import LobbyService


def _make_lobby(lobby_id: str, name: str = "") -> Lobby:
    """Create a valid Lobby with an organizer"""
    return Lobby(
        id=lobby_id,
        name=name,
        people=PersonGroup(
            [Person(identifier="p1", roles={GameRole.ORGANIZER, GameRole.PLAYER})]
        ),
    )


class TestLobbyService(TestCase):
    """Unit tests to ensure lobby service works as expected"""

    def test_save_lobby(self):
        """Lobby can be saved to the DB"""
        lobby = _make_lobby(str(time()))

        self.assertIsNotNone(LobbyService.save(lobby))

    def test_get_lobby(self):
        """Lobby can be retrieved from the DB"""
        original_lobby = _make_lobby(str(time()))
        LobbyService.save(original_lobby)
        lobby = LobbyService.get(original_lobby.id)

        self.assertIsNotNone(lobby)
        self.assertEqual(lobby.id, original_lobby.id)

    def test_get_non_existent_lobby(self):
        """Unknown lobby cannot be retrieved from the DB"""
        self.assertRaises(ValueError, LobbyService.get, str(time()))

    def test_search_lobby(self):
        """Lobbies can be searched in the DB"""
        text = f"search_test{time()}"
        lobbies = [
            LobbyService.save(_make_lobby(str(time()), name=f"{text} {i}"))
            for i in range(5)
        ]

        found_lobbies = LobbyService.search(
            SearchLobby(name=text, client="p1"),
            len(lobbies) + 1,
        )

        self.assertEqual(len(found_lobbies), len(lobbies))

    def test_start_game(self):
        """Lobby can be converted to a game"""
        lobby = _make_lobby(str(time()))
        lobby.join("p2")
        LobbyService.save(lobby)

        game = LobbyService.start_game(lobby)

        self.assertIsNotNone(game)
        self.assertEqual(game.id, lobby.id)
