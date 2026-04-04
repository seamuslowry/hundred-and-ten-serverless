"""A mapper to convert internal models to engine models"""

from hundredandten import round as engine_round

from src.main.models import internal


def round_events(r: engine_round.Round) -> list[internal.Event]:
    """Deserialize an engine round to the corresponding events"""
    trick_events: list[list[internal.Event]] = [
        [
            internal.TrickStart(),
            *[internal.Play.from_engine(p) for p in trick.plays],
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
        *[internal.Bid.from_engine(b) for b in r.bids],
        *([internal.SelectTrump.from_engine(r.selection)] if r.selection else []),
        *[internal.Discard.from_engine(b) for b in r.discards],
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

    return [
        internal.Card.from_engine(c)
        for c in (discard.cards + discard.kept if discard else player.hand)
    ]
