"""A module to convert client objects to models"""

from utils import models
from utils.decorators.authentication import get_identity
from utils.dtos import client
from utils.mappers.shared.deserialize import card as __deserialize_card


def user_id() -> str:
    """Get the authenticated user's identifier from context"""
    return get_identity().id


def user(c_user: client.User) -> models.User:
    """Convert a User model from a passed client request and user"""
    return models.User(
        identifier=user_id(),
        name=c_user["name"],
        picture_url=c_user["picture_url"],
    )


def card(c_card: client.Card) -> models.Card:
    """Create a card object from a passed client card"""
    return __deserialize_card(c_card)
