"""User Service unit tests"""

from time import time

from src.main.models.internal import User
from src.main.services import UserService


async def test_save_unknown_user():
    """User can be saved to the DB"""
    user = User(identifier=str(time()), name="save_unknown")

    assert (await UserService.save(user)) is not None


async def test_search_user():
    """Users can be searched in the DB"""
    text = f"search_user{time()}"
    users = [
        await UserService.save(User(identifier=str(time()), name=f"{text} {i}"))
        for i in range(5)
    ]

    found_users = await UserService.search(text)

    assert users == found_users


async def test_get_users_by_identifiers():
    """Users can be retrieved by identifier in the DB"""
    users = [
        await UserService.save(User(identifier=str(time()), name="search"))
        for _ in range(5)
    ]

    found_users = await UserService.by_identifiers(
        list(map(lambda u: u.identifier, users))
    )

    assert users == found_users
