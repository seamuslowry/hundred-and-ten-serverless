"""A module to convert DB DTOs to models"""

from utils import models
from utils.dtos import db
from utils.mappers.shared.deserialize import card as __card
from utils.models.lobby import PersonGroup


def user(db_user: db.User) -> models.User:
    """Convert a User DB DTO to its model"""
    return models.User(
        identifier=db_user["identifier"],
        name=db_user["name"],
        picture_url=db_user["picture_url"],
    )


def lobby(db_lobby: db.Lobby) -> models.Lobby:
    """Convert a Lobby DB DTO to its model"""
    return models.Lobby(
        id=db_lobby["id"],
        name=db_lobby["name"],
        seed=db_lobby["seed"],
        accessibility=models.Accessibility[db_lobby["accessibility"]],
        people=PersonGroup(map(__person, db_lobby["people"])),
    )


def game(db_game: db.Game) -> models.Game:
    """Convert a Game DB DTO to its model"""
    return models.Game(
        id=db_game["id"],
        name=db_game["name"],
        seed=db_game["seed"],
        accessibility=models.Accessibility[db_game["accessibility"]],
        people=PersonGroup(map(__person, db_game["people"])),
        initial_moves=list(map(__move, db_game["moves"])),
    )


def __person(person: db.Person) -> models.Person:
    return models.Person(
        identifier=person["identifier"],
        automate=person["automate"],
        roles={models.GameRole[r] for r in person["roles"]},
    )


def __move(db_move: db.Move) -> models.Action:
    """Convert a DB move to a game action"""
    identifier = db_move["identifier"]

    match db_move["type"]:
        case "bid":
            return models.Bid(
                identifier=identifier,
                amount=models.BidAmount(db_move["amount"]),
            )
        case "select_trump":
            return models.SelectTrump(
                identifier=identifier,
                suit=models.SelectableSuit[db_move["suit"]],
            )
        case "discard":
            return models.Discard(
                identifier=identifier,
                cards=list(map(__card, db_move["cards"])),
            )
        case "play":
            return models.Play(
                identifier=identifier,
                card=__card(db_move["card"]),
            )
        case _:  # type: ignore[unreachable]
            raise ValueError(f"Unknown move type: {db_move['type']}")
