"""Facilitate interaction with the lobby DB"""

from typing import Any, cast

from beanie.operators import ElemMatch, Or, RegEx

from src.main.mappers.db import deserialize, serialize
from src.main.models.client.requests import SearchLobbiesRequest
from src.main.models.db import Lobby as DbLobby
from src.main.models.internal import Accessibility, Game, Lobby


class LobbyService:
    """A service used to handle the business logic of lobbies"""

    @staticmethod
    async def save(lobby: Lobby) -> Lobby:
        """Save the provided lobby to the DB"""
        return deserialize.lobby(await serialize.lobby(lobby).save())

    @staticmethod
    async def get(lobby_id: str) -> Lobby:
        """Retrieve the lobby with the provided ID"""
        result = await DbLobby.get(lobby_id)

        if not result:
            raise ValueError(f"No lobby found with id {lobby_id}")

        return deserialize.lobby(result)

    @staticmethod
    async def search(player_id: str, search_lobby: SearchLobbiesRequest) -> list[Lobby]:
        """Search for lobbies matching the provided criteria"""
        return list(
            map(
                deserialize.lobby,
                await DbLobby.find(
                    RegEx(DbLobby.name, search_lobby.searchText, "i"),
                    Or(
                        DbLobby.accessibility == Accessibility.PUBLIC,
                        ElemMatch(DbLobby.players, {"identifier": player_id}),
                        ElemMatch(DbLobby.invitees, {"identifier": player_id}),
                        DbLobby.organizer.identifier == player_id,
                    ),
                )
                .limit(search_lobby.limit)
                .skip(search_lobby.offset)
                .to_list(),
            )
        )

    @staticmethod
    async def start_game(lobby: Lobby) -> Game:
        """Convert a lobby to a game (starts the game)"""
        client = cast(Any, DbLobby).get_pymongo_collection().database.client
        game = Game.from_lobby(lobby)

        async with client.start_session() as session:
            async with await session.start_transaction():
                saved_game = await serialize.game(game).save(session=session)
                await serialize.lobby(lobby).delete(session=session)
                return deserialize.game(saved_game)
