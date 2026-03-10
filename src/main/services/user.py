"""Facilitate interaction with the user DB"""

from typing import Optional

from beanie.operators import In, RegEx, Set

from src.main.mappers.db import deserialize, serialize
from src.main.models.db import User as DbUser
from src.main.models.internal import User

MAX = 20


class UserService:
    """A service used to handle the business logic of users"""

    @staticmethod
    async def save(user: User) -> User:
        """Save the provided user to the DB"""
        serialized_user = serialize.user(user)
        await DbUser.find_one(
            DbUser.identifier == user.identifier, with_children=True
        ).upsert(
            Set(serialized_user.model_dump()),
            on_insert=serialized_user,
        )  # type: ignore upsert does need to be awaited, but doesn't get typed as such

        new_user = await DbUser.find_one(DbUser.identifier == user.identifier, with_children=True)
        assert new_user
        return deserialize.user(new_user)

    @staticmethod
    async def search(search_text: str) -> list[User]:
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
    async def by_identifier(identifier: str) -> Optional[User]:
        """Retrieve the user with identifier provided"""
        result = await DbUser.find_one(
            DbUser.identifier == identifier, with_children=True
        )

        if not result:
            return None
        return deserialize.user(result)

    @staticmethod
    async def by_identifiers(identifiers: list[str]) -> list[User]:
        """Retrieve the users with identifiers in the list provided"""
        return list(
            map(
                deserialize.user,
                await DbUser.find(
                    In(DbUser.identifier, identifiers), with_children=True
                ).to_list(),
            )
        )
