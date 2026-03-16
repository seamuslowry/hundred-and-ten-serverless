"""Facilitate interaction with the user DB"""

from beanie.operators import In, RegEx

from src.main.mappers.db import deserialize, serialize
from src.main.models.db import Player as DbUser
from src.main.models.internal import Player

MAX = 20


class UserService:
    """A service used to handle the business logic of users"""

    @staticmethod
    async def save(user: Player) -> Player:
        """Save the provided user to the DB"""
        serialized_user = serialize.player(user)

        existing_user = await DbUser.find_one(
            DbUser.player_id == user.player_id, with_children=True
        )

        if existing_user:
            serialized_user.id = existing_user.id

        return deserialize.user(await serialized_user.save())

    @staticmethod
    async def search(search_text: str) -> list[Player]:
        """Retrieve the users with names like the provided"""
        return list(
            map(
                deserialize.user,
                await DbUser.find(
                    RegEx(DbUser.name, search_text, "i"), with_children=True
                )
                .limit(MAX)
                .to_list(),
            )
        )

    @staticmethod
    async def by_identifiers(identifiers: list[str]) -> list[Player]:
        """Retrieve the users with identifiers in the list provided"""
        return list(
            map(
                deserialize.user,
                await DbUser.find(
                    In(DbUser.player_id, identifiers), with_children=True
                ).to_list(),
            )
        )
