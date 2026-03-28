"""A mapper to convert internal models to engine models"""

from hundredandten import actions, deck
from hundredandten import round as engine_round

from src.main.models import internal


def action(a: actions.Action) -> internal.Action:
    match (a):
        case actions.Bid():
            return internal.Bid(a.identifier, a.amount.value)
        case actions.SelectTrump():
            return internal.SelectTrump(a.identifier, internal.CardSuit[a.suit.name])
        case actions.Discard() | actions.DetailedDiscard():
            return internal.Discard(a.identifier, [card(c) for c in a.cards])
        case actions.Play():
            return internal.Play(a.identifier, card(a.card))
    raise ValueError(f"Could not convert engine action {a} to an internal action")


def round_events(r: engine_round.Round) -> list[internal.Event]:
    trick_events: list[list[internal.Event]] = [
        [
            internal.TrickStart(),
            *[action(p) for p in trick.plays],
            # don't include the trick end event if it hasn't ended
            *(
                [internal.TrickEnd(trick.winning_play.identifier)]
                if (trick.winning_play and len(trick.plays) == len(r.players))
                else []
            ),
        ]
        for trick in r.tricks
    ]

    return [
        internal.RoundStart(
            r.dealer.identifier,
            {p.identifier: _original_hand(r, p.identifier) for p in r.players},
        ),
        *[action(b) for b in r.bids],
        *([action(r.selection)] if r.selection else []),
        *[action(b) for b in r.discards],
        *[trick_event for event_list in trick_events for trick_event in event_list],
        # don't include the round end event if it hasn't ended
        *(
            [internal.RoundEnd(scores={s.identifier: s.value for s in r.scores})]
            if r.completed
            else []
        ),
    ]


def _original_hand(r: engine_round.Round, player_id: str) -> list[internal.Card]:
    """Return the identified player's original hand"""
    player = next(p for p in r.players if p.identifier == player_id)
    discard = next((d for d in r.discards if d.identifier == player_id), None)

    return [card(c) for c in (discard.cards + discard.kept if discard else player.hand)]


def card(c: deck.Card) -> internal.Card:
    """Convert an engine card model to an internal card model"""
    return internal.Card(
        suit=internal.CardSuit[c.suit.name], number=internal.CardNumber(c.number.name)
    )
