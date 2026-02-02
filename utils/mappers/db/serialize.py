"""A module to convert models to DB DTOs"""

from utils import models
from utils.dtos import db


def game(m_game: models.Game) -> db.Game:
    """Convert a Game model to its DB DTO"""
    active_player = (
        m_game.active_round.active_player
        if not m_game.lobby and m_game._game and not m_game._game.winner
        else None
    )
    return db.Game(
        id=m_game.id,
        name=m_game.name,
        seed=m_game.seed,
        accessibility=m_game.accessibility.name,
        people=list(map(__person, m_game.people)),
        winner=m_game.winner.identifier if m_game.winner else None,
        active_player=active_player.identifier if active_player else None,
        moves=list(map(__move, m_game.moves)),
        lobby=m_game.lobby,
        status=m_game.status.name,
    )


def user(m_user: models.User) -> db.User:
    """Convert a User model to its DB DTO"""
    return db.User(
        identifier=m_user.identifier, name=m_user.name, picture_url=m_user.picture_url
    )


def __card(card: models.Card) -> db.Card:
    return db.Card(suit=card.suit.name, number=card.number.name)


def __person(person: models.Person) -> db.Person:
    return db.Person(
        identifier=person.identifier,
        roles=list(map(lambda r: r.name, person.roles)),
        automate=person.automate,
    )


def __move(move: models.Action) -> db.Move:
    """Convert a game action to a DB move"""
    if isinstance(move, models.Bid):
        return db.BidMove(
            type="bid",
            identifier=move.identifier,
            amount=move.amount.value,
        )
    if isinstance(move, models.SelectTrump):
        return db.SelectTrumpMove(
            type="select_trump",
            identifier=move.identifier,
            suit=move.suit.name,
        )
    if isinstance(move, models.Discard):
        return db.DiscardMove(
            type="discard",
            identifier=move.identifier,
            cards=list(map(__card, move.cards)),
        )
    if isinstance(move, models.Play):
        return db.PlayMove(
            type="play",
            identifier=move.identifier,
            card=__card(move.card),
        )
    if isinstance(move, models.Unpass):
        return db.UnpassMove(
            type="unpass",
            identifier=move.identifier,
        )
    raise ValueError(f"Unknown move type: {type(move)}")
