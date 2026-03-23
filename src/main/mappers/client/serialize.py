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
) -> responses.Game:
    """Return a game as it can be provided to the client"""
    assert m_game.id  # games sent to clients will be saved and have an id

    if m_game.status == internal.GameStatus.WON:
        assert m_game.winner  # won games will have winners
        return responses.CompletedGame(
            id=m_game.id,
            name=m_game.name,
            status=m_game.status.name,
            scores=m_game.scores,
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
        players=[__player_in_game(p) for p in m_game.ordered_players],
    )


def events(
    m_events: list[internal.Event], client_player_id: str
) -> list[responses.Event]:
    """Return a list of events as they can be provided to the client"""
    return [
        __event(event, index, client_player_id) for index, event in enumerate(m_events)
    ]


def suggestion(m_action: internal.Action) -> responses.UnorderedActionResponse:
    """Return a suggested action as it can be provided to the client"""
    if isinstance(m_action, internal.Bid):
        return responses.QueuedBid(
            type="BID", amount=m_action.amount, player_id=m_action.identifier
        )
    if isinstance(m_action, internal.SelectTrump):
        return responses.QueuedSelectTrump(
            type="SELECT_TRUMP",
            suit=SelectableSuit[m_action.suit.name],
            player_id=m_action.identifier,
        )
    if isinstance(m_action, internal.Discard):
        return responses.QueuedDiscard(
            type="DISCARD",
            cards=[__card(c) for c in m_action.cards],
            player_id=m_action.identifier,
        )
    if isinstance(m_action, internal.Play):
        return responses.QueuedPlayCard(
            type="PLAY", card=__card(m_action.card), player_id=m_action.identifier
        )
    raise ValueError("No suggestion available at this time")


def __play(play: internal.Play) -> responses.QueuedPlayCard:
    return responses.QueuedPlayCard(
        type="PLAY", player_id=play.identifier, card=__card(play.card)
    )


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
        queued_actions=(
            [suggestion(a) for a in player_in_game.queued_actions]
            if isinstance(player_in_game, internal.Human)
            else []
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


def __event(
    event: internal.Event, sequence: int, client_player_id: str
) -> responses.Event:
    """Convert the provided event into the structure it should provide the client"""
    result: Optional[responses.Event] = None

    if isinstance(event, internal.GameStart):
        result = responses.GameStart(type="GAME_START", sequence=sequence)
    elif isinstance(event, internal.RoundStart):
        result = responses.RoundStart(
            type="ROUND_START",
            sequence=sequence,
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
        result = responses.BidAction(
            type="BID",
            sequence=sequence,
            player_id=event.identifier,
            amount=event.amount.value,
        )

    elif isinstance(event, internal.SelectTrump):
        result = responses.SelectTrumpAction(
            type="SELECT_TRUMP",
            sequence=sequence,
            player_id=event.identifier,
            suit=SelectableSuit[event.suit.name],
        )
    elif isinstance(event, internal.Discard):
        result = responses.DiscardAction(
            type="DISCARD",
            sequence=sequence,
            player_id=event.identifier,
            cards=(
                [__card(c) for c in event.cards]
                if client_player_id == event.identifier
                else len(event.cards)
            ),
        )
    elif isinstance(event, internal.TrickStart):
        result = responses.TrickStart(type="TRICK_START", sequence=sequence)
    elif isinstance(event, internal.Play):
        result = responses.PlayCardAction(
            type="PLAY",
            sequence=sequence,
            player_id=event.identifier,
            card=__card(event.card),
        )
    elif isinstance(event, internal.TrickEnd):
        result = responses.TrickEnd(
            type="TRICK_END",
            sequence=sequence,
            winner_player_id=event.winner,
        )
    elif isinstance(event, internal.RoundEnd):
        result = responses.RoundEnd(
            type="ROUND_END",
            sequence=sequence,
            scores=[__score(s) for s in event.scores],
        )
    elif isinstance(event, internal.GameEnd):
        result = responses.GameEnd(
            type="GAME_END",
            sequence=sequence,
            winner_player_id=event.winner,
        )

    if result is None:
        raise ValueError(f"Unknown event type: {type(event).__name__}")

    return result


def __score(score: internal.Score) -> responses.Score:
    return responses.Score(player_id=score.identifier, value=score.value)
