"""A module to convert DB DTOs to models"""

from src.main.models import internal
from src.main.models.db import db


def user(db_user: db.User) -> internal.User:
    """Convert a User DB DTO to its model"""
    return internal.User(
        identifier=db_user["identifier"],
        name=db_user["name"],
        picture_url=db_user["picture_url"],
    )


def lobby(db_lobby: db.Lobby) -> internal.Lobby:
    """Convert a Lobby DB DTO to its model"""
    return internal.Lobby(
        id=str(db_lobby["_id"]) if "_id" in db_lobby else None,
        name=db_lobby["name"],
        seed=db_lobby["seed"],
        accessibility=internal.Accessibility[db_lobby["accessibility"]],
        organizer=__person(db_lobby["organizer"]),
        players=internal.PersonGroup(map(__person, db_lobby["players"])),
        invitees=internal.PersonGroup(map(__person, db_lobby["invitees"])),
    )


def game(db_game: db.Game) -> internal.Game:
    """Convert a Game DB DTO to its model"""
    return internal.Game(
        id=str(db_game["_id"]) if "_id" in db_game else None,
        name=db_game["name"],
        seed=db_game["seed"],
        accessibility=internal.Accessibility[db_game["accessibility"]],
        organizer=__person(db_game["organizer"]),
        players=internal.PersonGroup(map(__person, db_game["players"])),
        initial_moves=list(map(__move, db_game["moves"])),
    )


def __person(person: db.Person) -> internal.Person:
    return (
        internal.NaiveCpu(identifier=person["identifier"])
        if person["automate"]
        else internal.Human(identifier=person["identifier"])
    )


def __move(db_move: db.Move) -> internal.Action:
    """Convert a DB move to a game action"""
    identifier = db_move["identifier"]

    match db_move["type"]:
        case "bid":
            return internal.Bid(
                identifier=identifier,
                amount=internal.BidAmount(db_move["amount"]),
            )
        case "select_trump":
            return internal.SelectTrump(
                identifier=identifier,
                suit=internal.SelectableSuit[db_move["suit"]],
            )
        case "discard":
            return internal.Discard(
                identifier=identifier,
                cards=list(map(__card, db_move["cards"])),
            )
        case "play":
            return internal.Play(
                identifier=identifier,
                card=__card(db_move["card"]),
            )
        case _:  # type: ignore[unreachable]
            raise ValueError(f"Unknown move type: {db_move['type']}")


def __card(db_card: db.Card) -> internal.Card:
    """Convert a card from the DB to its model"""
    suit = None

    try:
        suit = internal.SelectableSuit[db_card["suit"]]
    except KeyError:
        pass

    try:
        suit = internal.UnselectableSuit[db_card["suit"]]
    except KeyError:
        pass

    assert suit

    return internal.Card(suit=suit, number=internal.CardNumber[db_card["number"]])
