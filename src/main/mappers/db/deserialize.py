"""A module to convert DB DTOs to models"""

from src.main.models import db, internal


def user(db_user: db.User) -> internal.User:
    """Convert a User DB DTO to its model"""
    return internal.User(
        id=str(db_user.id) if db_user.id else None,
        player_id=db_user.identifier,
        name=db_user.name,
        picture_url=db_user.picture_url,
    )


def lobby(db_lobby: db.Lobby) -> internal.Lobby:
    """Convert a Lobby DB DTO to its model"""
    return internal.Lobby(
        id=str(db_lobby.id),
        name=db_lobby.name,
        accessibility=internal.Accessibility[db_lobby.accessibility.name],
        organizer=__person(db_lobby.organizer),
        players=internal.PersonGroup(map(__person, db_lobby.players)),
        invitees=internal.PersonGroup(map(__person, db_lobby.invitees)),
    )


def game(db_game: db.Game) -> internal.Game:
    """Convert a Game DB DTO to its model"""
    return internal.Game(
        id=str(db_game.id),
        name=db_game.name,
        seed=db_game.seed,
        accessibility=internal.Accessibility[db_game.accessibility.name],
        organizer=__person(db_game.organizer),
        players=internal.PersonGroup(map(__person, db_game.players)),
        initial_moves=list(map(__move, db_game.moves)),
    )


def __person(person: db.Player) -> internal.Person:
    if isinstance(person, db.NaiveCpuPlayer):
        return internal.NaiveCpu(identifier=person.identifier)
    if isinstance(person, db.HumanPlayer):
        return internal.Human(identifier=person.identifier)

    # type: ignore[unreachable]
    raise ValueError(f"Unknown player type ${person}")  # pragma: no cover


def __move(db_move: db.Move) -> internal.Action:
    """Convert a DB move to a game action"""
    identifier = db_move.identifier

    match db_move:
        case db.BidMove():
            return internal.Bid(
                identifier=identifier,
                amount=internal.BidAmount(db_move.amount),
            )
        case db.SelectTrumpMove():
            return internal.SelectTrump(
                identifier=identifier,
                suit=internal.SelectableSuit[db_move.suit],
            )
        case db.DiscardMove():
            return internal.Discard(
                identifier=identifier,
                cards=list(map(__card, db_move.cards)),
            )
        case db.PlayMove():
            return internal.Play(
                identifier=identifier,
                card=__card(db_move.card),
            )
        # type: ignore[unreachable]
        case _:  # pragma: no cover
            raise ValueError(f"Unknown move type: {db_move.type}")


def __card(db_card: db.Card) -> internal.Card:
    """Convert a card from the DB to its model"""
    suit = None

    try:
        suit = internal.SelectableSuit[db_card.suit.name]
    except KeyError:
        pass

    try:
        suit = internal.UnselectableSuit[db_card.suit.name]
    except KeyError:
        pass

    assert suit

    return internal.Card(suit=suit, number=internal.CardNumber[db_card.number.name])
