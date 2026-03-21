"""A module to convert models to client objects"""

from typing import Optional

from src.main.models import internal
from src.main.models.client import responses
from src.main.models.client.constants import CardNumberName, SelectableSuit, Suit


def player(m_player: internal.Player) -> responses.Player:
    """Return a player as it can be provided to the client"""
    return responses.Player(
        id=m_player.player_id,
        name=m_player.name or m_player.player_id,
        picture_url=m_player.picture_url,
    )


def lobby(
    m_lobby: internal.Lobby,
) -> responses.WaitingGame:
    """Return a lobby as it can be provided to the client"""
    assert m_lobby.id  # lobbies sent to the client will be saved and have an id

    return responses.WaitingGame(
        id=m_lobby.id,
        name=m_lobby.name,
        status=internal.GameStatus.WAITING_FOR_PLAYERS.name,
        accessibility=m_lobby.accessibility.name,
        organizer=__player_in_game(m_lobby.organizer),
        players=[
            __player_in_game(p) for p in m_lobby.players if p != m_lobby.organizer
        ],
        invitees=[
            __player_in_game(p) for p in m_lobby.invitees if p not in m_lobby.players
        ],
    )


def game(
    m_game: internal.Game,
    client_player_id: str,
    initial_event_knowledge: Optional[int] = None,
) -> responses.Game:
    """Return a game as it can be provided to the client"""
    client_events = (
        events(m_game.events[initial_event_knowledge:], client_player_id)
        if initial_event_knowledge is not None
        else []
    )
    assert m_game.id  # games sent to clients will be saved and have an id

    if m_game.status == internal.GameStatus.WON:
        assert m_game.winner  # won games will have winners
        return responses.CompletedGame(
            id=m_game.id,
            name=m_game.name,
            status=m_game.status.name,
            scores=m_game.scores,
            results=client_events,
            winner=__player_in_game(m_game.winner),
            organizer=__player_in_game(m_game.organizer),
            players=[__player_in_game(p) for p in m_game.ordered_players],
        )

    return responses.StartedGame(
        id=m_game.id,
        name=m_game.name,
        status=m_game.status.name,
        round=__round(m_game.active_round, client_player_id),
        scores=m_game.scores,
        results=client_events,
        players=[__player_in_game(p) for p in m_game.ordered_players],
    )


def events(
    m_events: list[internal.Event], client_player_id: str
) -> list[responses.Event]:
    """Return a list of events as they can be provided to the client"""
    return [__event(e, client_player_id) for e in m_events]


def action(m_action: internal.Action) -> responses.GameAction:
    """Return a suggested action as it can be provided to the client"""
    if isinstance(m_action, internal.Bid):
        return responses.BidAction(
            amount=m_action.amount, player_id=m_action.identifier
        )
    if isinstance(m_action, internal.SelectTrump):
        return responses.SelectTrumpAction(
            suit=SelectableSuit[m_action.suit.name], player_id=m_action.identifier
        )
    if isinstance(m_action, internal.Discard):
        return responses.DiscardAction(
            discards=[__card(c) for c in m_action.cards], player_id=m_action.identifier
        )
    if isinstance(m_action, internal.Play):
        return responses.PlayCardAction(
            card=__card(m_action.card), player_id=m_action.identifier
        )
    raise ValueError("No suggestion available at this time")


def __play(play: internal.Play) -> responses.PlayCardAction:
    return responses.PlayCardAction(player_id=play.identifier, card=__card(play.card))


def __trick(trick: internal.Trick) -> responses.Trick:
    return responses.Trick(
        bleeding=trick.bleeding,
        winning_play=__play(trick.winning_play) if trick.winning_play else None,
        plays=[__play(p) for p in trick.plays],
    )


def __round(m_round: internal.Round, client_player_id: str) -> responses.Round:
    non_zero_bids = [bid for bid in m_round.bids if bid.amount > 0]
    current_bid = (
        non_zero_bids[-1]
        if non_zero_bids
        else internal.Bid("", internal.BidAmount.PASS)
    )
    bidder = m_round.active_bidder

    return responses.Round(
        players=[__player_in_round(p, client_player_id) for p in m_round.players],
        dealer=__player_in_round(m_round.dealer, client_player_id),
        bidder=__player_in_round(bidder, client_player_id) if bidder else None,
        bid=current_bid.amount.value if current_bid.amount else None,
        trump=SelectableSuit[m_round.trump.name] if m_round.trump else None,
        tricks=[__trick(t) for t in m_round.tricks],
        active_player=(
            __player_in_round(m_round.active_player, client_player_id)
            if not m_round.completed
            else None
        ),
    )


def __player_in_game(player_in_game: internal.PlayerInGame) -> responses.PlayerInGame:
    return responses.PlayerInGame(
        id=player_in_game.id,
        automate=isinstance(player_in_game, internal.NaiveCpu),
        queued_action=(
            action(player_in_game.queued_action)
            if isinstance(player_in_game, internal.Human)
            and player_in_game.queued_action is not None
            else None
        ),
    )


def __player_in_round(
    round_player: internal.RoundPlayer, client_player_id: str
) -> responses.PlayerInRound:
    if round_player.identifier == client_player_id:
        return responses.SelfInRound(
            id=round_player.identifier,
            hand=[__card(c) for c in round_player.hand],
        )

    return responses.OtherPlayerInRound(
        id=round_player.identifier,
        hand_size=len(round_player.hand),
    )


def __card(card: internal.Card) -> responses.Card:
    return responses.Card(
        suit=Suit[card.suit.name], number=CardNumberName[card.number.name]
    )


def __event(event: internal.Event, client_player_id: str) -> responses.Event:
    """Convert the provided event into the structure it should provide the client"""
    result: Optional[responses.Event] = None

    if isinstance(event, internal.GameStart):
        result = __game_start_event()
    elif isinstance(event, internal.RoundStart):
        result = __round_start_event(event, client_player_id)
    elif isinstance(event, internal.Bid):
        result = __bid_event(event)
    elif isinstance(event, internal.SelectTrump):
        result = __select_trump_event(event)
    elif isinstance(event, internal.Discard):
        result = __discard_event(event, client_player_id)
    elif isinstance(event, internal.TrickStart):
        result = __trick_start_event()
    elif isinstance(event, internal.Play):
        result = __play_event(event)
    elif isinstance(event, internal.TrickEnd):
        result = __trick_end_event(event)
    elif isinstance(event, internal.RoundEnd):
        result = __round_end_event(event)
    elif isinstance(event, internal.GameEnd):
        result = __game_end_event(event)

    if result is None:
        raise ValueError(f"Unknown event type: {type(event).__name__}")

    return result


def __game_start_event() -> responses.GameStart:
    return responses.GameStart()


def __round_start_event(
    event: internal.RoundStart, client_player_id: str
) -> responses.RoundStart:
    return responses.RoundStart(
        dealer=event.dealer,
        hands={
            player_id: (
                [__card(c) for c in hand]
                if player_id == client_player_id
                else len(hand)
            )
            for player_id, hand in event.hands.items()
        },
    )


def __bid_event(event: internal.Bid) -> responses.BidAction:
    return responses.BidAction(
        player_id=event.identifier,
        amount=event.amount.value,
    )


def __select_trump_event(event: internal.SelectTrump) -> responses.SelectTrumpAction:
    return responses.SelectTrumpAction(
        player_id=event.identifier,
        suit=SelectableSuit[event.suit.name],
    )


def __discard_event(
    event: internal.Discard, client_player_id: str
) -> responses.DiscardAction:
    return responses.DiscardAction(
        player_id=event.identifier,
        discards=(
            [__card(c) for c in event.cards]
            if client_player_id == event.identifier
            else len(event.cards)
        ),
    )


def __trick_start_event() -> responses.TrickStart:
    return responses.TrickStart()


def __play_event(event: internal.Play) -> responses.PlayCardAction:
    return responses.PlayCardAction(
        player_id=event.identifier,
        card=__card(event.card),
    )


def __trick_end_event(event: internal.TrickEnd) -> responses.TrickEnd:
    return responses.TrickEnd(
        winner_player_id=event.winner,
    )


def __score(score: internal.Score) -> responses.Score:
    return responses.Score(player_id=score.identifier, value=score.value)


def __round_end_event(event: internal.RoundEnd) -> responses.RoundEnd:
    return responses.RoundEnd(
        scores=[__score(s) for s in event.scores],
    )


def __game_end_event(event: internal.GameEnd) -> responses.GameEnd:
    return responses.GameEnd(
        winner_player_id=event.winner,
    )
