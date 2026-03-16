"""A module to convert models to DB DTOs"""

from beanie import PydanticObjectId

from src.main.models import db, internal


def lobby(m_lobby: internal.Lobby) -> db.Lobby:
    """Convert a Lobby model to its DB DTO"""
    result = db.LobbyV0(
        id=PydanticObjectId(m_lobby.id) if m_lobby.id else None,
        name=m_lobby.name,
        accessibility=db.Accessibility[m_lobby.accessibility.name],
        organizer=__person(m_lobby.organizer),
        players=list(map(__person, m_lobby.players)),
        invitees=list(map(__person, m_lobby.invitees)),
    )

    return result


def game(m_game: internal.Game) -> db.Game:
    """Convert a Game model to its DB DTO"""
    winner = m_game.winner.identifier if m_game.winner else None
    active_player = (
        m_game.active_round.active_player.identifier
        if m_game.status != internal.GameStatus.WON
        else None
    )

    return db.GameV0(
        id=PydanticObjectId(m_game.id) if m_game.id else None,
        name=m_game.name,
        seed=m_game.seed,
        accessibility=db.Accessibility[m_game.accessibility.name],
        organizer=__person(m_game.organizer),
        players=list(map(__person, m_game.players)),
        winner=winner,
        active_player=active_player,
        moves=list(map(__move, m_game.moves)),
        status=db.Status[m_game.status.name],
    )


def user(m_user: internal.User) -> db.User:
    """Convert a User model to its DB DTO"""
    return db.UserV0(
        id=PydanticObjectId(m_user.id) if m_user.id else None,
        identifier=m_user.player_id,
        name=m_user.name or m_user.player_id,
        picture_url=m_user.picture_url,
    )


def __card(card: internal.Card) -> db.Card:
    return db.Card(suit=db.Suit[card.suit.name], number=db.CardNumber[card.number.name])


def __person(person: internal.Person) -> db.Player:
    match person:
        case internal.Human():
            return __human(person)
        case internal.NaiveCpu():
            return db.NaiveCpuPlayer(identifier=person.identifier)

    raise ValueError(f"Unrecognized player type ${person}")


def __human(person: internal.Human) -> db.HumanPlayer:
    return db.HumanPlayer(identifier=person.identifier)


def __move(move: internal.Action) -> db.Move:
    """Convert a game action to a DB move"""
    if isinstance(move, internal.Bid):
        return db.BidMove(
            type="bid",
            identifier=move.identifier,
            amount=move.amount.value,
        )
    if isinstance(move, internal.SelectTrump):
        return db.SelectTrumpMove(
            type="select_trump",
            identifier=move.identifier,
            suit=db.SelectableSuit[move.suit.name],
        )
    if isinstance(move, internal.Discard):
        return db.DiscardMove(
            type="discard",
            identifier=move.identifier,
            cards=list(map(__card, move.cards)),
        )
    if isinstance(move, internal.Play):
        return db.PlayMove(
            type="play",
            identifier=move.identifier,
            card=__card(move.card),
        )
    raise ValueError(f"Unknown move type: {type(move)}")  # pragma: no cover
