"""A module to convert client objects to models"""

from utils import models
from utils.dtos import requests


def user(identifier: str, c_user: requests.UpdateUserRequest) -> models.User:
    """Convert a User model from a passed client request and user"""
    return models.User(
        identifier=identifier,
        name=c_user.name,
        picture_url=c_user.picture_url,
    )


def card(c_card: requests.CardRequest) -> models.Card:
    """Create a card object from a passed client card"""
    suit = None

    try:
        suit = models.SelectableSuit[c_card.suit]
    except KeyError:
        pass

    try:
        suit = models.UnselectableSuit[c_card.suit]
    except KeyError:
        pass

    assert suit

    return models.Card(suit=suit, number=models.CardNumber[c_card.number])
