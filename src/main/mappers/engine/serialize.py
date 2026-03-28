"""A mapper to convert internal models to engine models"""

from hundredandten import actions, constants, deck

from src.main.models import internal


def card(c: internal.Card) -> deck.Card:
    """Convert an internal card model to an engine card model"""
    # TODO: engine shouldn't make this so painful
    if c.suit == internal.CardSuit.JOKER:
        suit = constants.UnselectableSuit.JOKER
    else:
        suit = constants.SelectableSuit[c.suit.name]

    return deck.Card(suit=suit, number=constants.CardNumber[c.number.name])


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
                identifier=a.player_id, cards=[card(c) for c in a.cards]
            )
        case internal.Play():
            return actions.Play(identifier=a.player_id, card=card(a.card))
