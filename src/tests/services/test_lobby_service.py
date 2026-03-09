"""Lobby Service unit tests"""

from unittest import TestCase

from bson import ObjectId

from src.main.models.client.requests import SearchLobbiesRequest
from src.main.models.internal import Human, Lobby
from src.main.services import LobbyService


def _make_lobby(name: str = "") -> Lobby:
    """Create a valid Lobby with an organizer"""
    return Lobby(name=name, organizer=Human("p1"))


class TestLobbyService(TestCase):
    """Unit tests to ensure lobby service works as expected"""

    async def test_save_lobby(self):
        """Lobby can be saved to the DB and receives a generated id"""
        lobby = _make_lobby()

        self.assertIsNone(lobby.id)
        lobby = await LobbyService.save(lobby)
        self.assertIsNotNone(lobby.id)

    async def test_get_lobby(self):
        """Lobby can be retrieved from the DB"""
        original_lobby = _make_lobby()
        original_lobby = await LobbyService.save(original_lobby)
        assert original_lobby.id
        lobby = await LobbyService.get(original_lobby.id)

        self.assertIsNotNone(lobby)
        self.assertEqual(lobby.id, original_lobby.id)

    def test_get_non_existent_lobby(self):
        """Unknown lobby cannot be retrieved from the DB"""
        self.assertRaises(ValueError, LobbyService.get, str(ObjectId()))

    async def test_search_lobby(self):
        """Lobbies can be searched in the DB"""
        text = f"search_test{ObjectId()}"
        lobbies = [LobbyService.save(_make_lobby(name=f"{text} {i}")) for i in range(5)]

        found_lobbies = await LobbyService.search(
            "p1",
            SearchLobbiesRequest(searchText=text, limit=len(lobbies) + 1),
        )

        self.assertEqual(len(found_lobbies), len(lobbies))

    async def test_start_game(self):
        """Lobby can be converted to a game"""
        lobby = _make_lobby()
        lobby.join(Human("p2"))
        await LobbyService.save(lobby)

        game = await LobbyService.start_game(lobby)

        self.assertIsNotNone(game)
        self.assertEqual(game.id, lobby.id)

    async def test_start_game_requires_minimum_players(self):
        """Lobby cannot be converted to a game with fewer than 2 players"""
        lobby = _make_lobby()
        await LobbyService.save(lobby)

        self.assertRaises(ValueError, LobbyService.start_game, lobby)
