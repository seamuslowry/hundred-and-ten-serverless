"""A mapper to convert internal models to engine models"""

from hundredandten import actions, constants

from src.main.models import internal


def action(a: internal.Action) -> actions.Action:
    """Convert an internal action model to an engine action model"""
    match a:
        case internal.Bid():
            return actions.Bid(
                identifier=a.player_id, amount=constants.BidAmount(a.amount)
            )
        case internal.SelectTrump():
            return actions.SelectTrump(
                identifier=a.player_id, suit=constants.SelectableSuit[a.suit.name]
            )
        case internal.Discard():
            return actions.Discard(
                identifier=a.player_id, cards=[c.to_engine() for c in a.cards]
            )
        case internal.Play():
            return actions.Play(identifier=a.player_id, card=a.card.to_engine())

    raise ValueError(f"Unable to serialize unrecognized {a}")  # pragma: no cover
