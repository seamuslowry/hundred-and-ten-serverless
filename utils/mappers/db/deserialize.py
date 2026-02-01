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

    # If there are rounds, the game has started - reconstruct the game engine
    if db_game["rounds"]:
        rounds = list(map(__round, db_game["rounds"]))

        # Create players for the game engine from the people who are players
        game_players = models.Group(
            [
                models.Player(identifier=p.identifier, automate=p.automate)
                for p in m_game.players
            ]
        )

        # Create the game engine with the same seed
        m_game._game = models.HundredAndTen(players=game_players, seed=m_game.seed)

        # Replace the rounds with our deserialized ones
        # Note: This is a workaround since v2's game engine manages rounds internally
        m_game._game._rounds = rounds

    return m_game


def __person(person: db.Person) -> models.Person:
    return models.Person(
        identifier=person["identifier"],
        automate=person["automate"],
        roles=set(map(lambda r: models.GameRole[r], person["roles"])),
    )


def __player(player: db.Player) -> models.Player:
    return models.Player(
        identifier=player["identifier"],
        automate=player["automate"],
        roles=set(map(lambda r: models.RoundRole[r], player["roles"])),
        hand=list(map(__card, player["hand"])),
    )


def __bid(bid: db.Bid) -> models.Bid:
    return models.Bid(
        identifier=bid["identifier"], amount=models.BidAmount(bid["amount"])
    )


def __deck(deck: db.Deck) -> models.Deck:
    return models.Deck(seed=deck["seed"], pulled=deck["pulled"])


def __discard(discard: db.Discard) -> models.DetailedDiscard:
    return models.DetailedDiscard(
        identifier=discard["identifier"],
        cards=list(map(__card, discard["cards"])),
        kept=list(map(__card, discard["kept"])),
    )


def __play(play: db.Play) -> models.Play:
    return models.Play(identifier=play["identifier"], card=__card(play["card"]))


def __trick(trick: db.Trick) -> models.Trick:
    return models.Trick(
        plays=list(map(__play, trick["plays"])),
        round_trump=models.SelectableSuit[trick["round_trump"]],
    )


def __round(db_round: db.Round) -> models.Round:

    trump_name = db_round["trump"]
    trump = models.SelectableSuit[trump_name] if trump_name else None

    model_round = models.Round(
        players=models.Group(map(__player, db_round["players"])),
        bids=list(map(__bid, db_round["bids"])),
        deck=__deck(db_round["deck"]),
        discards=list(map(__discard, db_round["discards"])),
        tricks=list(map(__trick, db_round["tricks"])),
    )

    active_bidder = model_round.active_bidder
    model_round.selection = (
        models.SelectTrump(active_bidder.identifier, trump)
        if (active_bidder and trump)
        else None
    )

    return model_round
