'''A module to convert models to client objects'''

from typing import Optional

from app import models
from app.dtos import client
from app.mappers.constants import EventType


def user(m_user: models.User) -> client.User:
    '''Return a user as it can be provided to the client'''
    return client.User(
        identifier=m_user.identifier,
        name=m_user.name,
        picture_url=m_user.picture_url if isinstance(m_user, models.GoogleUser) else None
    )


def game(m_game: models.Game,
         client_identifier: str,
         initial_event_knowledge: Optional[int] = None) -> client.Game:
    '''Return a game as it can be provided to the client'''
    if m_game.status == models.GameStatus.WAITING_FOR_PLAYERS:
        return client.WaitingGame(
            id=m_game.id,
            name=m_game.name,
            status=m_game.status.name,
            accessibility=m_game.accessibility.name,
            organizer=__person(m_game.organizer),
            players=list(map(__person, (p for p in m_game.players if p != m_game.organizer))),
            invitees=list(map(__person, (p for p in m_game.invitees if p not in m_game.players)))
        )

    return client.StartedGame(
        id=m_game.id, name=m_game.name, status=m_game.status.name,
        round=__round(m_game.active_round, client_identifier),
        scores=m_game.scores,
        results=events(m_game.events[initial_event_knowledge:],
                       client_identifier) if initial_event_knowledge is not None else None)


def events(m_events: list[models.Event], client_identifier: str) -> list[client.Event]:
    '''Return a list of events as they can be provided to the client'''
    return list(map(lambda e: __event(e, client_identifier), m_events))


def suggestion(m_suggestion: models.Action, client_identifier: str) -> client.Suggestion:
    '''Return a suggested action as it can be provided to the client'''
    if client_identifier != m_suggestion.identifier:
        raise ValueError('You can only ask for a suggestion on your turn')

    if isinstance(m_suggestion, models.Bid):
        return client.BidSuggestion(
            amount=m_suggestion.amount
        )
    if isinstance(m_suggestion, models.SelectTrump):
        return client.SelectTrumpSuggestion(
            suit=m_suggestion.suit.name
        )
    if isinstance(m_suggestion, models.Discard):
        return client.DiscardSuggestion(
            cards=list(map(__card, m_suggestion.cards))
        )
    if isinstance(m_suggestion, models.Play):
        return client.PlaySuggestion(
            card=__card(m_suggestion.card)
        )
    return client.Suggestion()


def __play(play: models.Play) -> client.Play:
    return client.Play(
        identifier=play.identifier,
        card=__card(play.card)
    )


def __trick(trick: models.Trick) -> client.Trick:
    return client.Trick(
        bleeding=trick.bleeding,
        winning_play=__play(trick.winning_play) if trick.winning_play else None,
        plays=list(map(__play, trick.plays))
    )


def __round(m_round: models.Round, client_identifier: str) -> client.Round:
    non_zero_bids = [bid for bid in m_round.bids if bid.amount > 0]
    current_bid = non_zero_bids[-1] if non_zero_bids else models.Bid('', models.BidAmount.PASS)
    bidder = m_round.players.by_identifier(current_bid.identifier)

    return client.Round(
        players=list(map(lambda p: __player(p, client_identifier), m_round.players)),
        dealer=__player(m_round.dealer, client_identifier),
        bidder=__player(bidder, client_identifier) if bidder else None,
        bid=current_bid.amount.value if current_bid.amount else None,
        trump=m_round.trump.name if m_round.trump else None,
        tricks=list(map(__trick, m_round.tricks)),
        active_player=(
            __player(m_round.active_player, client_identifier)
            if not m_round.completed else None)
    )


def __person(person: models.Person) -> client.Person:
    return client.Person(
        identifier=person.identifier,
        automate=person.automate,
        prepassed=models.RoundRole in person.roles
    )


def __player(player: models.Player, client_identifier: str) -> client.Player:
    if player.identifier == client_identifier:
        return client.Self(
            identifier=player.identifier,
            automate=player.automate,
            prepassed=models.RoundRole in player.roles,
            hand=list(map(__card, player.hand))
        )

    return client.OtherPlayer(
        identifier=player.identifier,
        automate=player.automate,
        prepassed=models.RoundRole in player.roles,
        hand_size=len(player.hand)
    )


def __card(card: models.Card) -> client.Card:
    return client.Card(
        suit=card.suit.name,
        number=card.number.name
    )


def __event(event: models.Event, client_identifier: str) -> client.Event:
    '''Convert the provided event into the structure it should provide the client'''
    ret = client.Event(type='unknown')
    if isinstance(event, models.GameStart):
        ret = __game_start_json()
    if isinstance(event, models.RoundStart):
        ret = __round_start_json(event, client_identifier)
    if isinstance(event, models.Bid):
        ret = __bid_json(event)
    if isinstance(event, models.SelectTrump):
        ret = __select_trump_json(event)
    if isinstance(event, models.Discard):
        ret = __discard_json(event, client_identifier)
    if isinstance(event, models.TrickStart):
        ret = __trick_start_json()
    if isinstance(event, models.Play):
        ret = __play_json(event)
    if isinstance(event, models.TrickEnd):
        ret = __trick_end_json(event)
    if isinstance(event, models.RoundEnd):
        ret = __round_end_json(event)
    if isinstance(event, models.GameEnd):
        ret = __game_end_json(event)
    return ret


def __game_start_json() -> client.GameStart:
    return {
        "type": EventType.GAME_START.name
    }


def __round_start_json(event: models.RoundStart, client_identifier: str) -> client.RoundStart:
    return {
        "type": EventType.ROUND_START.name,
        "dealer": event.dealer,
        "hands": ({identifier: list(map(__card, hand))
                   if identifier == client_identifier else len(hand)
                   for identifier, hand in event.hands.items()})
    }


def __bid_json(event: models.Bid) -> client.Bid:
    return {
        "type": EventType.BID.name,
        "identifier": event.identifier,
        "amount": event.amount.value
    }


def __select_trump_json(event: models.SelectTrump) -> client.SelectTrump:
    return {
        "type": EventType.SELECT_TRUMP.name,
        "identifier": event.identifier,
        "suit": event.suit.name
    }


def __discard_json(event: models.Discard, client_identifier: str) -> client.Discard:
    return {
        "type": EventType.DISCARD.name,
        "identifier": event.identifier,
        "discards": (list(map(__card, event.cards))
                     if client_identifier == event.identifier else len(event.cards))
    }


def __trick_start_json() -> client.TrickStart:
    return {
        "type": EventType.TRICK_START.name
    }


def __play_json(event: models.Play) -> client.PlayEvent:
    return {
        "type": EventType.PLAY.name,
        "identifier": event.identifier,
        "card": __card(event.card)
    }


def __trick_end_json(event: models.TrickEnd) -> client.TrickEnd:
    return {
        "type": EventType.TRICK_END.name,
        "winner": event.winner
    }


def __round_end_json(event: models.RoundEnd) -> client.RoundEnd:
    return {
        "type": EventType.ROUND_END.name,
        "scores": event.scores
    }


def __game_end_json(event: models.GameEnd) -> client.GameEnd:
    return {
        "type": EventType.GAME_END.name,
        "winner": event.winner
    }
