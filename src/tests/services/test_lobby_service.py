"""Lobby Service unit tests"""

import pytest
from bson import ObjectId

from src.main.models.client.requests import SearchLobbiesRequest
from src.main.models.internal import Human, Lobby
from src.main.services import LobbyService


def _make_lobby(name: str = "") -> Lobby:
    """Create a valid Lobby with an organizer"""
    return Lobby(name=name, organizer=Human("p1"))


class TestLobbyService:
    """Unit tests to ensure lobby service works as expected"""

    async def test_save_lobby(self):
        """Lobby can be saved to the DB and receives a generated id"""
        lobby = _make_lobby()

        assert lobby.id is None
        lobby = await LobbyService.save(lobby)
        assert lobby.id is not None

    async def test_get_lobby(self):
        """Lobby can be retrieved from the DB"""
        original_lobby = _make_lobby()
        original_lobby = await LobbyService.save(original_lobby)
        assert original_lobby.id
        lobby = await LobbyService.get(original_lobby.id)

        assert lobby is not None
        assert lobby.id == original_lobby.id

    async def test_get_non_existent_lobby(self):
        """Unknown lobby cannot be retrieved from the DB"""
        with pytest.raises(ValueError):
            await LobbyService.get(str(ObjectId()))

    async def test_search_lobby(self):
        """Lobbies can be searched in the DB"""
        text = f"search_test{ObjectId()}"
        lobbies = []
        for i in range(5):
            lobbies.append(await LobbyService.save(_make_lobby(name=f"{text} {i}")))

        found_lobbies = await LobbyService.search(
            "p1",
            SearchLobbiesRequest(search_text=text, limit=len(lobbies) + 1),
        )

        assert len(found_lobbies) == len(lobbies)

    async def test_start_game(self):
        """Lobby can be converted to a game"""
        lobby = _make_lobby()
        lobby.join(Human("p2"))
        lobby = await LobbyService.save(lobby)

        game = await LobbyService.start_game(lobby)

        assert game is not None
        assert game.id == lobby.id

    async def test_start_game_requires_minimum_players(self):
        """Lobby cannot be converted to a game with fewer than 2 players"""
        lobby = _make_lobby()
        await LobbyService.save(lobby)

        with pytest.raises(ValueError):
            await LobbyService.start_game(lobby)
