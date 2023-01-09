'''A module to convert DB DTOs to models'''

from app import models
from app.dtos import db
from app.mappers.constants import UserType
from app.mappers.shared.deserialize import card as __card


def user(db_user: db.User) -> models.User:
    '''Convert a User model to its DB DTO'''
    if db_user['type'] == UserType.GOOGLE:
        return models.GoogleUser(
            db_user['identifier'], db_user['name'], db_user['picture_url'] or ''
        )

    return models.User(
        identifier=db_user['identifier'],
        name=db_user['name']
    )


def game(db_game: db.Game) -> models.Game:
    '''Convert a Game DB DTO to its model'''
    return models.Game(
        id=db_game['id'],
        name=db_game['name'],
        seed=db_game['seed'],
        accessibility=models.Accessibility[db_game['accessibility']],
        people=models.Group(map(__person, db_game['people'])),
        rounds=list(map(__round, db_game['rounds']))
    )


def __person(person: db.Person) -> models.Person:
    return models.Person(
        identifier=person['identifier'],
        automate=person['automate'],
        roles=set(map(lambda r: models.GameRole[r], person['roles']))
    )


def __player(player: db.Player) -> models.Player:
    return models.Player(
        identifier=player['identifier'],
        automate=player['automate'],
        roles=set(map(lambda r: models.RoundRole[r], player['roles'])),
        hand=list(map(__card, player['hand']))
    )


def __bid(bid: db.Bid) -> models.Bid:
    return models.Bid(
        identifier=bid['identifier'],
        amount=models.BidAmount(bid['amount'])
    )


def __deck(deck: db.Deck) -> models.Deck:
    return models.Deck(
        seed=deck['seed'],
        pulled=deck['pulled']
    )


def __discard(discard: db.Discard) -> models.DetailedDiscard:
    return models.DetailedDiscard(
        identifier=discard['identifier'],
        cards=list(map(__card, discard['cards'])),
        kept=list(map(__card, discard['kept']))
    )


def __play(play: db.Play) -> models.Play:
    return models.Play(
        identifier=play['identifier'],
        card=__card(play['card'])
    )


def __trick(trick: db.Trick) -> models.Trick:
    return models.Trick(
        plays=list(map(__play, trick['plays'])),
        round_trump=models.SelectableSuit[trick['round_trump']]
    )


def __round(db_round: db.Round) -> models.Round:

    trump_name = db_round['trump']
    trump = models.SelectableSuit[trump_name] if trump_name else None

    model_round = models.Round(
        players=models.Group(map(__player, db_round['players'])),
        bids=list(map(__bid, db_round['bids'])),
        deck=__deck(db_round['deck']),
        discards=list(map(__discard, db_round['discards'])),
        tricks=list(map(__trick, db_round['tricks']))
    )

    active_bidder = model_round.active_bidder
    model_round.selection = models.SelectTrump(active_bidder.identifier,
                                               trump) if (active_bidder and trump) else None

    return model_round
