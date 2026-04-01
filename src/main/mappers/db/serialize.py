"""A module to convert models to DB DTOs"""

from beanie import PydanticObjectId

from src.main.models import db, internal


def lobby(m_lobby: internal.Lobby) -> db.Lobby:
    """Convert a Lobby model to its DB DTO"""
    result = db.LobbyV0(
        id=PydanticObjectId(m_lobby.id) if m_lobby.id else None,
        name=m_lobby.name,
        accessibility=db.Accessibility[m_lobby.accessibility.name],
        organizer=__player_in_game(m_lobby.organizer),
        players=list(map(__player_in_game, m_lobby.players)),
        invitees=list(map(__player_in_game, m_lobby.invitees)),
    )

    return result


def game(m_game: internal.Game) -> db.Game:
    """Convert a Game model to its DB DTO"""
    winner = m_game.winner.id if m_game.winner else None
    active_player = (
        m_game.active_player_id if m_game.status != internal.GameStatus.WON else None
    )

    return db.GameV0(
        id=PydanticObjectId(m_game.id) if m_game.id else None,
        name=m_game.name,
        seed=m_game.seed,
        accessibility=db.Accessibility[m_game.accessibility.name],
        organizer=__player_in_game(m_game.organizer),
        players=list(map(__player_in_game, m_game.players)),
        winner_player_id=winner,
        active_player_id=active_player,
        moves=list(map(__move, m_game.actions)),
        status=db.Status[m_game.status.name],
    )


def player(m_player: internal.Player) -> db.Player:
    """Convert a User model to its DB DTO"""
    return db.PlayerV0(
        id=PydanticObjectId(m_player.id) if m_player.id else None,
        player_id=m_player.player_id,
        name=m_player.name or m_player.player_id,
        picture_url=m_player.picture_url,
    )


def __card(card: internal.Card) -> db.Card:
    return db.Card(suit=db.Suit[card.suit.name], number=db.CardNumber[card.number.name])


def __player_in_game(person: internal.PlayerInGame) -> db.PlayerInGame:
    match person:
        case internal.Human():
            return __human(person)
        case internal.NaiveCpu():
            return db.NaiveCpuPlayer(player_id=person.id)

    raise ValueError(f"Unrecognized player type {person}")


def __human(person: internal.Human) -> db.HumanPlayer:
    return db.HumanPlayer(
        player_id=person.id,
        queued_actions=[__move(action) for action in person.queued_actions],
    )


def __move(move: internal.Action) -> db.Move:
    """Convert a game action to a DB move"""
    if isinstance(move, internal.Bid):
        return db.BidMove(
            type="bid",
            player_id=move.player_id,
            amount=move.amount,
        )
    if isinstance(move, internal.SelectTrump):
        return db.SelectTrumpMove(
            type="select_trump",
            player_id=move.player_id,
            suit=db.SelectableSuit[move.suit.name],
        )
    if isinstance(move, internal.Discard):
        return db.DiscardMove(
            type="discard",
            player_id=move.player_id,
            cards=list(map(__card, move.cards)),
        )
    if isinstance(move, internal.Play):
        return db.PlayMove(
            type="play",
            player_id=move.player_id,
            card=__card(move.card),
        )
    raise ValueError(f"Unknown move type: {type(move)}")  # pragma: no cover
