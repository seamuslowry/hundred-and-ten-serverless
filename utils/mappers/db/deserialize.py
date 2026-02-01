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

    # Create the game with lobby data
    m_game = models.Game(
        id=db_game["id"],
        name=db_game["name"],
        seed=db_game["seed"],
        accessibility=models.Accessibility[db_game["accessibility"]],
        people=PersonGroup(map(__person, db_game["people"])),
    )

    # If the game has started, reconstruct the game engine by replaying moves
    if db_game["started"]:
        m_game.start_game()

        # Replay all moves
        for move in db_game["moves"]:
            action = __move(move)
            m_game.act(action)

    return m_game


def __person(person: db.Person) -> models.Person:
    return models.Person(
        identifier=person["identifier"],
        automate=person["automate"],
        roles=set(map(lambda r: models.GameRole[r], person["roles"])),
    )


def __move(db_move: db.Move) -> models.Action:
    """Convert a DB move to a game action"""
    move_type = db_move["type"]
    identifier = db_move["identifier"]

    if move_type == "bid":
        return models.Bid(
            identifier=identifier,
            amount=models.BidAmount(db_move["amount"]),  # type: ignore
        )
    if move_type == "select_trump":
        return models.SelectTrump(
            identifier=identifier,
            suit=models.SelectableSuit[db_move["suit"]],  # type: ignore
        )
    if move_type == "discard":
        return models.Discard(
            identifier=identifier,
            cards=list(map(__card, db_move["cards"])),  # type: ignore
        )
    if move_type == "play":
        return models.Play(
            identifier=identifier,
            card=__card(db_move["card"]),  # type: ignore
        )
    if move_type == "unpass":
        return models.Unpass(identifier=identifier)

    raise ValueError(f"Unknown move type: {move_type}")
