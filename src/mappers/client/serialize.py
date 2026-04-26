"""A module to convert models to client objects"""

from typing import Optional

from src.models import internal
from src.models.client import responses
from src.models.client.constants import CardNumberName, SelectableSuit, Suit


def player(m_player: internal.Player) -> responses.Player:
    """Return a player as it can be provided to the client"""
    return responses.Player(
        id=m_player.player_id,
        name=m_player.name or m_player.player_id,
        picture_url=m_player.picture_url,
    )


def lobby(
    m_lobby: internal.Lobby,
) -> responses.LobbyResponse:
    """Return a lobby as it can be provided to the client"""
    assert m_lobby.id  # lobbies sent to the client will be saved and have an id

    return responses.LobbyResponse(
        id=m_lobby.id,
        name=m_lobby.name,
        accessibility=m_lobby.accessibility.name,
        organizer=__player_in_game(m_lobby.organizer),
        players=[
            __player_in_game(p) for p in m_lobby.players if p != m_lobby.organizer
        ],
        invitees=[
            __player_in_game(p) for p in m_lobby.invitees if p not in m_lobby.players
        ],
    )


def events(
    m_events: list[internal.Event], client_player_id: str
) -> list[responses.Event]:
    """Return a list of events as they can be provided to the client"""
    return [
        responses.Event(
            sequence=index, content=__event_content(event, client_player_id)
        )
        for index, event in enumerate(m_events)
    ]


def game(
    m_game: internal.Game,
    client_player_id: str,
) -> responses.GameResponse:
    """Return a round-based game response for the given player"""
    assert m_game.id  # games sent to clients will be saved and have an id

    game_rounds = m_game.rounds
    completed_rounds = game_rounds if m_game.winner else game_rounds[:-1]

    return responses.GameResponse(
        id=m_game.id,
        name=m_game.name,
        active=(
            responses.WonInformation(status="WON", winner_player_id=m_game.winner.id)
            if m_game.winner
            else __active_round(game_rounds[-1], m_game, client_player_id)
        ),
        players=[__player_in_game(p) for p in m_game.ordered_players],
        scores=m_game.scores,
        completed_rounds=[__completed_round(r) for r in completed_rounds],
    )


def __completed_round(
    m_round: internal.Round,
) -> responses.CompletedRound:
    bid = m_round.max_bid

    initial_hands = {
        player_id: [__card(c) for c in hand]
        for player_id, hand in m_round.initial_hands.items()
    }

    if bid is not None and m_round.trump is not None:
        return responses.CompletedWithBidderRound(
            status="COMPLETED",
            dealer_player_id=m_round.dealer_player_id,
            bid=__bid(bid),
            trump=SelectableSuit[m_round.trump.name],
            bid_history=[__bid(b) for b in m_round.bid_history],
            initial_hands=initial_hands,
            discards={
                player_id: __discard_record(record)
                for player_id, record in m_round.discards.items()
            },
            tricks=[__trick(t) for t in m_round.tricks],
            scores=m_round.scores,
        )

    return responses.CompletedNoBiddersRound(
        status="COMPLETED_NO_BIDDERS",
        dealer_player_id=m_round.dealer_player_id,
        initial_hands=initial_hands,
    )


def __active_round(
    m_round: internal.Round,
    m_game: internal.Game,
    client_player_id: str,
) -> responses.ActiveRound:
    """Convert an internal Round to an active round for the client"""
    # Active round: apply visibility rules
    requesting_player = m_game.ordered_players.find(client_player_id)
    queued = (
        [action(a) for a in requesting_player.queued_actions]
        if isinstance(requesting_player, internal.Human)
        else []
    )

    assert m_game.status != internal.GameStatus.WON

    bid = m_round.max_bid

    return responses.ActiveRound(
        status=m_game.status.name,
        dealer_player_id=m_round.dealer_player_id,
        bid_history=[__bid(b) for b in m_round.bid_history],
        bid=__bid(bid) if bid else None,
        hands={
            player_id: (
                [__card(c) for c in hand]
                if player_id == client_player_id
                else len(hand)
            )
            for player_id, hand in m_round.current_hands.items()
        },
        discards={
            player_id: (
                __discard_record(record)
                if player_id == client_player_id
                else len(record.discarded)
            )
            for player_id, record in m_round.discards.items()
        },
        trump=(SelectableSuit[m_round.trump.name] if m_round.trump else None),
        tricks=[__trick(t) for t in m_round.tricks],
        active_player_id=m_game.active_player_id,
        queued_actions=queued,
    )


def __discard_record(discard: internal.DiscardRecord) -> responses.DiscardRecord:
    return responses.DiscardRecord(
        discarded=[__card(c) for c in discard.discarded],
        received=[__card(c) for c in discard.received],
    )


def action(m_action: internal.Action) -> responses.GameAction:
    """Return an action as it can be provided to the client"""
    if isinstance(m_action, internal.Bid):
        return __bid(m_action)
    if isinstance(m_action, internal.SelectTrump):
        return __select_trump(m_action)
    if isinstance(m_action, internal.Discard):
        return __discard(m_action)
    if isinstance(m_action, internal.Play):
        return __play(m_action)
    # type: ignore[unreachable]
    raise ValueError("No suggestion available at this time")  # pragma: no cover


def __bid(b: internal.Bid) -> responses.BidAction:
    return responses.BidAction(type="BID", amount=b.amount, player_id=b.player_id)


def __play(play: internal.Play) -> responses.PlayCardAction:
    return responses.PlayCardAction(
        type="PLAY", player_id=play.player_id, card=__card(play.card)
    )


def __discard(discard: internal.Discard) -> responses.DiscardAction:
    return responses.DiscardAction(
        type="DISCARD",
        cards=[__card(c) for c in discard.cards],
        player_id=discard.player_id,
    )


def __select_trump(select: internal.SelectTrump) -> responses.SelectTrumpAction:
    return responses.SelectTrumpAction(
        type="SELECT_TRUMP",
        suit=SelectableSuit[select.suit.name],
        player_id=select.player_id,
    )


def __trick(trick: internal.Trick) -> responses.Trick:
    return responses.Trick(
        bleeding=trick.bleeding,
        winning_play=__play(trick.winning_play) if trick.winning_play else None,
        plays=[__play(p) for p in trick.plays],
    )


def __player_in_game(player_in_game: internal.PlayerInGame) -> responses.PlayerInGame:
    return responses.PlayerInGame(
        id=player_in_game.id, type=__player_type(player_in_game)
    )


def __player_type(player_in_game: internal.PlayerInGame) -> responses.PlayerType:
    match player_in_game:
        case internal.Human():
            return responses.PlayerType.HUMAN
        case internal.NaiveCpu():
            return responses.PlayerType.CPU_EASY

    raise ValueError(f"Unrecognized player type {player_in_game}")


def __card(card: internal.Card) -> responses.Card:
    return responses.Card(
        suit=Suit[card.suit.name], number=CardNumberName[card.number.name]
    )


def __event_content(
    event: internal.Event, client_player_id: str
) -> responses.EventContent:
    """Convert the provided event into the content it should provide the client"""
    content: Optional[responses.EventContent] = None

    if isinstance(event, internal.GameStart):
        content = responses.GameStart(type="GAME_START")
    elif isinstance(event, internal.RoundStart):
        content = responses.RoundStart(
            type="ROUND_START",
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
    elif isinstance(event, internal.Bid):
        content = __bid(event)
    elif isinstance(event, internal.SelectTrump):
        content = __select_trump(event)
    elif isinstance(event, internal.Discard):
        content = __discard(event)
    elif isinstance(event, internal.TrickStart):
        content = responses.TrickStart(type="TRICK_START")
    elif isinstance(event, internal.Play):
        content = __play(event)
    elif isinstance(event, internal.TrickEnd):
        content = responses.TrickEnd(
            type="TRICK_END",
            winner_player_id=event.winner,
        )
    elif isinstance(event, internal.RoundEnd):
        content = responses.RoundEnd(
            type="ROUND_END",
            scores=[
                responses.Score(player_id=identifier, value=score)
                for identifier, score in event.scores.items()
            ],
        )
    elif isinstance(event, internal.GameEnd):
        content = responses.GameEnd(
            type="GAME_END",
            winner_player_id=event.winner,
        )
    else:
        # type: ignore[unreachable]
        raise ValueError(
            f"Unknown event type: {type(event).__name__}"
        )  # pragma: no cover

    return content
