"""A module to convert models to client objects"""

from typing import Optional

from utils import models
from utils.dtos import responses


def user(m_user: models.User) -> responses.User:
    """Return a user as it can be provided to the client"""
    return responses.User(
        identifier=m_user.identifier, name=m_user.name, picture_url=m_user.picture_url
    )


def lobby(
    m_lobby: models.Lobby,
) -> responses.WaitingGame:
    """Return a lobby as it can be provided to the client"""
    assert m_lobby.id  # lobbies sent to the client will be saved and have an id

    return responses.WaitingGame(
        id=m_lobby.id,
        name=m_lobby.name,
        status=models.GameStatus.WAITING_FOR_PLAYERS.name,
        accessibility=m_lobby.accessibility.name,
        organizer=__person(m_lobby.organizer),
        players=[__person(p) for p in m_lobby.players if p != m_lobby.organizer],
        invitees=[__person(p) for p in m_lobby.invitees if p not in m_lobby.players],
    )


def game(
    m_game: models.Game,
    client_identifier: str,
    initial_event_knowledge: Optional[int] = None,
) -> responses.Game:
    """Return a game as it can be provided to the client"""
    client_events = (
        events(m_game.events[initial_event_knowledge:], client_identifier)
        if initial_event_knowledge is not None
        else []
    )
    assert m_game.id  # games sent to clients will be saved and have an id

    if m_game.status == models.GameStatus.WON:
        assert m_game.winner  # won games will have winners
        return responses.CompletedGame(
            id=m_game.id,
            name=m_game.name,
            status=m_game.status.name,
            scores=m_game.scores,
            results=client_events,
            winner=__person(m_game.winner),
            organizer=__person(m_game.organizer),
            players=[__person(p) for p in m_game.ordered_players],
        )

    return responses.StartedGame(
        id=m_game.id,
        name=m_game.name,
        status=m_game.status.name,
        round=__round(m_game.active_round, client_identifier),
        scores=m_game.scores,
        results=client_events,
    )


def events(
    m_events: list[models.Event], client_identifier: str
) -> list[responses.GameEvent]:
    """Return a list of events as they can be provided to the client"""
    return [__event(e, client_identifier) for e in m_events]


def suggestion(
    m_suggestion: models.Action, client_identifier: str
) -> responses.Suggestion:
    """Return a suggested action as it can be provided to the client"""
    if client_identifier != m_suggestion.identifier:
        raise ValueError("You can only ask for a suggestion on your turn")

    if isinstance(m_suggestion, models.Bid):
        return responses.BidSuggestion(amount=m_suggestion.amount)
    if isinstance(m_suggestion, models.SelectTrump):
        return responses.SelectTrumpSuggestion(suit=m_suggestion.suit.name)
    if isinstance(m_suggestion, models.Discard):
        return responses.DiscardSuggestion(
            cards=[__card(c) for c in m_suggestion.cards]
        )
    if isinstance(m_suggestion, models.Play):
        return responses.PlaySuggestion(card=__card(m_suggestion.card))
    raise ValueError("No suggestion available at this time")


def __play(play: models.Play) -> responses.Play:
    return responses.Play(identifier=play.identifier, card=__card(play.card))


def __trick(trick: models.Trick) -> responses.Trick:
    return responses.Trick(
        bleeding=trick.bleeding,
        winning_play=__play(trick.winning_play) if trick.winning_play else None,
        plays=[__play(p) for p in trick.plays],
    )


def __round(m_round: models.Round, client_identifier: str) -> responses.Round:
    non_zero_bids = [bid for bid in m_round.bids if bid.amount > 0]
    current_bid = (
        non_zero_bids[-1] if non_zero_bids else models.Bid("", models.BidAmount.PASS)
    )
    bidder = m_round.players.by_identifier(current_bid.identifier)

    return responses.Round(
        players=[__player(p, client_identifier) for p in m_round.players],
        dealer=__player(m_round.dealer, client_identifier),
        bidder=__player(bidder, client_identifier) if bidder else None,
        bid=current_bid.amount.value if current_bid.amount else None,
        trump=m_round.trump.name if m_round.trump else None,
        tricks=[__trick(t) for t in m_round.tricks],
        active_player=(
            __player(m_round.active_player, client_identifier)
            if not m_round.completed
            else None
        ),
    )


def __person(person: models.Person) -> responses.Person:
    return responses.Person(identifier=person.identifier, automate=person.automate)


def __player(player: models.RoundPlayer, client_identifier: str) -> responses.Player:
    if player.identifier == client_identifier:
        return responses.Self(
            identifier=player.identifier,
            automate=player.automate,
            prepassed=models.RoundRole.PRE_PASSED in player.roles,
            hand=[__card(c) for c in player.hand],
        )

    return responses.OtherPlayer(
        identifier=player.identifier,
        automate=player.automate,
        hand_size=len(player.hand),
    )


def __card(card: models.Card) -> responses.Card:
    return responses.Card(suit=card.suit.name, number=card.number.name)


def __event(event: models.Event, client_identifier: str) -> responses.GameEvent:
    """Convert the provided event into the structure it should provide the client"""
    if isinstance(event, models.GameStart):
        return __game_start_event()
    if isinstance(event, models.RoundStart):
        return __round_start_event(event, client_identifier)
    if isinstance(event, models.Bid):
        return __bid_event(event)
    if isinstance(event, models.SelectTrump):
        return __select_trump_event(event)
    if isinstance(event, models.Discard):
        return __discard_event(event, client_identifier)
    if isinstance(event, models.TrickStart):
        return __trick_start_event()
    if isinstance(event, models.Play):
        return __play_event(event)
    if isinstance(event, models.TrickEnd):
        return __trick_end_event(event)
    if isinstance(event, models.RoundEnd):
        return __round_end_event(event)
    if isinstance(event, models.GameEnd):
        return __game_end_event(event)
    # Fallback for unknown event types
    raise ValueError(f"Unknown event type: {type(event).__name__}")


def __game_start_event() -> responses.GameStart:
    return responses.GameStart()


def __round_start_event(
    event: models.RoundStart, client_identifier: str
) -> responses.RoundStart:
    return responses.RoundStart(
        dealer=event.dealer,
        hands={
            identifier: (
                [__card(c) for c in hand]
                if identifier == client_identifier
                else len(hand)
            )
            for identifier, hand in event.hands.items()
        },
    )


def __bid_event(event: models.Bid) -> responses.Bid:
    return responses.Bid(
        identifier=event.identifier,
        amount=event.amount.value,
    )


def __select_trump_event(event: models.SelectTrump) -> responses.SelectTrump:
    return responses.SelectTrump(
        identifier=event.identifier,
        suit=event.suit.name,
    )


def __discard_event(event: models.Discard, client_identifier: str) -> responses.Discard:
    return responses.Discard(
        identifier=event.identifier,
        discards=(
            [__card(c) for c in event.cards]
            if client_identifier == event.identifier
            else len(event.cards)
        ),
    )


def __trick_start_event() -> responses.TrickStart:
    return responses.TrickStart()


def __play_event(event: models.Play) -> responses.PlayEvent:
    return responses.PlayEvent(
        identifier=event.identifier,
        card=__card(event.card),
    )


def __trick_end_event(event: models.TrickEnd) -> responses.TrickEnd:
    return responses.TrickEnd(
        winner=event.winner,
    )


def __score(score: models.Score) -> responses.Score:
    return responses.Score(identifier=score.identifier, value=score.value)


def __round_end_event(event: models.RoundEnd) -> responses.RoundEnd:
    return responses.RoundEnd(
        scores=[__score(s) for s in event.scores],
    )


def __game_end_event(event: models.GameEnd) -> responses.GameEnd:
    return responses.GameEnd(
        winner=event.winner,
    )
