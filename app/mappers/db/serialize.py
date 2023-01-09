'''A module to convert models to DB DTOs'''
from typing import Optional

from app import models
from app.dtos import db
from app.mappers.constants import UserType


def game(m_game: models.Game) -> db.Game:
    '''Convert a Game model to its DB DTO'''
    winner = m_game.winner
    active_player = m_game.active_round.active_player if m_game.rounds and not winner else None

    return db.Game(
        id=m_game.id,
        status=m_game.status.name,
        name=m_game.name,
        seed=m_game.seed,
        accessibility=m_game.accessibility.name,
        people=list(map(__person, m_game.people)),
        rounds=list(map(__round, m_game.rounds)),
        active_player=active_player.identifier if active_player else None,
        winner=winner.identifier if winner else None
    )


def user(m_user: models.User) -> db.User:
    '''Convert a User model to its DB DTO'''
    return db.User(
        identifier=m_user.identifier,
        name=m_user.name,
        type=__user_type(m_user),
        picture_url=__user_picture(m_user))


def __card(card: models.Card) -> db.Card:
    return db.Card(
        suit=card.suit.name,
        number=card.number.name
    )


def __person(person: models.Person) -> db.Person:
    return db.Person(
        identifier=person.identifier,
        roles=list(map(lambda r: r.name, person.roles)),
        automate=person.automate
    )


def __player(player: models.Player) -> db.Player:
    return db.Player(
        identifier=player.identifier,
        roles=list(map(lambda r: r.name, player.roles)),
        automate=player.automate,
        hand=list(map(__card, player.hand))
    )


def __bid(bid: models.Bid) -> db.Bid:
    return db.Bid(
        identifier=bid.identifier,
        amount=bid.amount.value
    )


def __deck(deck: models.Deck) -> db.Deck:
    return db.Deck(
        seed=deck.seed,
        pulled=deck.pulled
    )


def __discard(discard: models.DetailedDiscard) -> db.Discard:
    return db.Discard(
        identifier=discard.identifier,
        cards=list(map(__card, discard.cards)),
        kept=list(map(__card, discard.kept))
    )


def __play(play: models.Play) -> db.Play:
    return db.Play(
        identifier=play.identifier,
        card=__card(play.card)
    )


def __trick(trick: models.Trick) -> db.Trick:
    return db.Trick(
        plays=list(map(__play, trick.plays)),
        round_trump=trick.round_trump.name
    )


def __round(m_round: models.Round) -> db.Round:
    return db.Round(
        players=list(map(__player, m_round.players)),
        bids=list(map(__bid, m_round.bids)),
        deck=__deck(m_round.deck),
        trump=m_round.trump.name if m_round.trump else None,
        discards=list(map(__discard, m_round.discards)),
        tricks=list(map(__trick, m_round.tricks))
    )


def __user_type(m_user: models.User) -> UserType:
    if isinstance(m_user, models.GoogleUser):
        return UserType.GOOGLE
    return UserType.UNKNOWN


def __user_picture(m_user: models.User) -> Optional[str]:
    if isinstance(m_user, models.GoogleUser):
        return m_user.picture_url
    return None
