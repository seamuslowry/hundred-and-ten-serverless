"""A module to convert DB DTOs to models"""

from pydantic import ValidationError

from utils import models
from utils.models import db
from utils.models.game import PersonGroup


def user(raw: db.User | dict) -> models.User:
    """Convert a User DB DTO to its model"""
    db_user = raw if isinstance(raw, db.User) else db.User.model_validate(raw)
    return models.User(
        identifier=db_user.identifier,
        name=db_user.name,
        picture_url=db_user.picture_url,
    )


def lobby(raw: db.Lobby | dict) -> models.Lobby:
    """Convert a Lobby DB DTO to its model"""
    db_lobby = raw if isinstance(raw, db.Lobby) else db.Lobby.model_validate(raw)
    return models.Lobby(
        id=db_lobby.id,
        name=db_lobby.name,
        seed=db_lobby.seed,
        accessibility=models.Accessibility[db_lobby.accessibility],
        organizer=__person(db_lobby.organizer),
        players=PersonGroup(map(__person, db_lobby.players)),
        invitees=PersonGroup(map(__person, db_lobby.invitees)),
    )


def game(raw: db.Game | dict) -> models.Game:
    """Convert a Game DB DTO to its model"""
    try:
        db_game = raw if isinstance(raw, db.Game) else db.Game.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc
    return models.Game(
        id=db_game.id,
        name=db_game.name,
        seed=db_game.seed,
        accessibility=models.Accessibility[db_game.accessibility],
        organizer=__person(db_game.organizer),
        players=PersonGroup(map(__person, db_game.players)),
        initial_moves=list(map(__move, db_game.moves)),
    )


def __person(person: db.Person) -> models.Person:
    return models.Person(
        identifier=person.identifier,
        automate=person.automate,
    )


def __move(db_move: db.Move) -> models.Action:
    """Convert a DB move to a game action"""
    if isinstance(db_move, db.BidMove):
        return models.Bid(
            identifier=db_move.identifier,
            amount=models.BidAmount(db_move.amount),
        )
    if isinstance(db_move, db.SelectTrumpMove):
        return models.SelectTrump(
            identifier=db_move.identifier,
            suit=models.SelectableSuit[db_move.suit],
        )
    if isinstance(db_move, db.DiscardMove):
        return models.Discard(
            identifier=db_move.identifier,
            cards=list(map(__card, db_move.cards)),
        )
    if isinstance(db_move, db.PlayMove):
        return models.Play(
            identifier=db_move.identifier,
            card=__card(db_move.card),
        )
    raise ValueError(f"Unknown move type: {type(db_move)}")  # pragma: no cover


def __card(db_card: db.Card) -> models.Card:
    """Convert a card from the DB to its model"""
    suit = None

    try:
        suit = models.SelectableSuit[db_card.suit]
    except KeyError:
        pass

    try:
        suit = models.UnselectableSuit[db_card.suit]
    except KeyError:
        pass

    assert suit

    return models.Card(suit=suit, number=models.CardNumber[db_card.number])
