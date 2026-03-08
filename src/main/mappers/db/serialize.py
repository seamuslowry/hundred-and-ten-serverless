"""A module to convert models to DB DTOs"""

from bson import ObjectId

from src.main.models import internal
from src.main.models.db import db


def lobby(m_lobby: internal.Lobby) -> db.Lobby:
    """Convert a Lobby model to its DB DTO"""
    result = db.Lobby(
        type="lobby",
        name=m_lobby.name,
        seed=m_lobby.seed,
        accessibility=m_lobby.accessibility.name,
        organizer=__person(m_lobby.organizer),
        players=list(map(__person, m_lobby.players)),
        invitees=list(map(__person, m_lobby.invitees)),
    )

    if m_lobby.id is not None:
        result["_id"] = ObjectId(m_lobby.id)

    return result


def game(m_game: internal.Game) -> db.Game:
    """Convert a Game model to its DB DTO"""
    active_player = m_game.active_round.active_player if not m_game.winner else None

    assert m_game.id  # games must have been created from existing lobby records

    return db.Game(
        type="game",
        _id=ObjectId(m_game.id),
        name=m_game.name,
        seed=m_game.seed,
        accessibility=m_game.accessibility.name,
        organizer=__person(m_game.organizer),
        players=list(map(__person, m_game.players)),
        winner=m_game.winner.identifier if m_game.winner else None,
        active_player=active_player.identifier if active_player else None,
        moves=list(map(__move, m_game.moves)),
        status=m_game.status.name,
    )


def user(m_user: internal.User) -> db.User:
    """Convert a User model to its DB DTO"""
    return db.User(
        identifier=m_user.identifier, name=m_user.name, picture_url=m_user.picture_url
    )


def __card(card: internal.Card) -> db.Card:
    return db.Card(suit=card.suit.name, number=card.number.name)


def __person(person: internal.Person) -> db.Person:
    return db.Person(
        identifier=person.identifier,
        automate=isinstance(person, internal.NaiveCpu),
    )


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
            suit=move.suit.name,
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
