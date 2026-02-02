"""A module to convert DB DTOs to models"""

from utils import models
from utils.dtos import db
from utils.mappers.shared.deserialize import card as __card
from utils.models.game import PersonGroup


def user(db_user: db.User) -> models.User:
    """Convert a User model to its DB DTO"""
    return models.User(
        identifier=db_user["identifier"],
        name=db_user["name"],
        picture_url=db_user["picture_url"],
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
        lobby=db_game["lobby"],
    )


def __person(person: db.Person) -> models.Person:
    return models.Person(
        identifier=person["identifier"],
        automate=person["automate"],
        roles=set(map(lambda r: models.GameRole[r], person["roles"])),
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
        case "unpass":
            return models.Unpass(identifier=identifier)
