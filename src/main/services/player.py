"""Facilitate interaction with the player DB"""

from beanie.operators import In, RegEx

from src.main.mappers.db import deserialize, serialize
from src.main.models.client.requests import SearchPlayersRequest
from src.main.models.db import Player as DbPlayer
from src.main.models.internal import Player
from src.main.models.internal.errors import NotFoundError


class PlayerService:
    """A service used to handle the business logic of players"""

    @staticmethod
    async def save(player: Player) -> Player:
        """Save the provided player to the DB"""
        serialized_player = serialize.player(player)

        existing_player = await DbPlayer.find_one(
            DbPlayer.player_id == player.player_id, with_children=True
        )

        if existing_player:
            serialized_player.id = existing_player.id

        return deserialize.player(await serialized_player.save())

    @staticmethod
    async def search(search_request: SearchPlayersRequest) -> list[Player]:
        """Retrieve the players with names like the provided"""
        return list(
            map(
                deserialize.player,
                await DbPlayer.find(
                    RegEx(DbPlayer.name, search_request.search_text, "i"),
                    with_children=True,
                )
                .skip(search_request.offset)
                .limit(search_request.limit)
                .to_list(),
            )
        )

    @staticmethod
    async def by_player_id(player_id: str) -> Player:
        """Retrieve the player with the player ID provided"""
        result = await DbPlayer.find_one(DbPlayer.player_id == player_id, with_children=True)
        if not result:
            raise NotFoundError(f"No player found with id {player_id}")

        return deserialize.player(result)

    @staticmethod
    async def by_player_ids(player_ids: list[str]) -> list[Player]:
        """Retrieve the players with the player IDs in the list provided"""
        return list(
            map(
                deserialize.player,
                await DbPlayer.find(
                    In(DbPlayer.player_id, player_ids), with_children=True
                ).to_list(),
            )
        )
