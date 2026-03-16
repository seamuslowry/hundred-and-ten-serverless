"""A module to convert client objects to models"""

from src.main.models.client import requests
from src.main.models.internal import (
    Card,
    CardNumber,
    SelectableSuit,
    UnselectableSuit,
)


def card(c_card: requests.CardRequest) -> Card:
    """Create a card object from a passed client card"""
    suit = None

    try:
        suit = SelectableSuit[c_card.suit.value]
    except KeyError:
        pass

    try:
        suit = UnselectableSuit[c_card.suit.value]
    except KeyError:
        pass

    assert suit

    return Card(suit=suit, number=CardNumber[c_card.number.value])
