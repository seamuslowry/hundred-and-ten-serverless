"""A module to convert client objects to models"""

from src.main.models import internal
from src.main.models.client import requests


def __card(c_card: requests.CardRequest) -> internal.Card:
    """Create a card object from a passed client card"""

    return internal.Card(
        suit=internal.CardSuit[c_card.suit.value],
        number=internal.CardNumber[c_card.number.value],
    )


def action(player_id: str, c_action: requests.ActRequest) -> internal.Action:
    """Create an action from a passed act request"""
    match c_action:
        case requests.BidRequest():
            return internal.Bid(player_id, internal.BidAmount(c_action.amount))
        case requests.SelectTrumpRequest():
            return internal.SelectTrump(
                player_id, internal.CardSuit[c_action.suit.value]
            )
        case requests.DiscardRequest():
            return internal.Discard(player_id, [__card(c) for c in c_action.cards])
        case requests.PlayRequest():
            return internal.Play(player_id, __card(c_action.card))

    # type: ignore[unreachable]
    raise ValueError(f"Unknown action type {c_action}")  # pragma: no cover
