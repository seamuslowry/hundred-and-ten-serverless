'''Facilitate interaction with the user DB'''

from typing import Optional

from utils.mappers.db import deserialize, serialize
from utils.models import User
from utils.services.mongo import user_client

MAX = 20


def save(user: User) -> User:
    '''Save the provided user to the DB'''
    user_client.update_one(
        {'identifier': user.identifier},
        {'$set': serialize.user(user)},
        upsert=True)
    return user


def search(search_text: str) -> list[User]:
    '''Retrieve the users with names like the provided'''
    return list(
        map(deserialize.user, user_client.find(
            {'name': {'$regex': search_text, '$options': 'i'}}).limit(MAX)))


def by_identifier(identifier: str) -> Optional[User]:
    '''Retrieve the user with identifier provided'''
    result = user_client.find_one({'identifier': identifier})

    if not result:
        return None
    return deserialize.user(result)


def by_identifiers(identifiers: list[str]) -> list[User]:
    '''Retrieve the users with identifiers in the list provided'''
    return list(
        map(deserialize.user, user_client.find(
            {'identifier': {'$in': identifiers}})))
