'''Deserialization behavior consistent between the client and the DB '''
from typing import Union

from utils import models
from utils.dtos import client, db


def card(m_card: Union[db.Card, client.Card]) -> models.Card:
    '''Convert a card from the client or the DB to its model'''
    suit = None

    try:
        suit = models.SelectableSuit[m_card['suit']]
    except KeyError:
        pass

    try:
        suit = models.UnselectableSuit[m_card['suit']]
    except KeyError:
        pass

    assert suit

    return models.Card(
        suit=suit,
        number=models.CardNumber[m_card['number']]
    )
