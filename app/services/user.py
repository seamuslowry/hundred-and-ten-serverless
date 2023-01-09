'''Facilitate interaction with the user DB'''

from app.mappers.db import deserialize, serialize
from app.models import User
from app.services.mongo import user_client

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


def by_identifiers(identifiers: list[str]) -> list[User]:
    '''Retrieve the users with identifiers in the list provided'''
    return list(
        map(deserialize.user, user_client.find(
            {'identifier': {'$in': identifiers}})))
