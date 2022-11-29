'''Facilitate interaction with the game DB'''
from typing import Optional

from app.models import Accessibility, Game, GameStatus, Group
from app.services import event, person
from app.services import round as round_service
from app.services.cosmos import game_client


def save(game: Game) -> Game:
    '''Save the provided game to the DB'''
    return from_db(game_client.upsert_item(to_db(game)))


def get(game_id: str) -> Game:
    '''Retrieve the game with the provided ID'''
    return from_db(game_client.read_item(game_id, game_id))


def to_db(game: Game) -> dict:
    '''Convert the provided game into the dict structure used by the DB'''
    return {
        'id': game.id,
        'status': game.status.name,
        'name': game.name,
        'seed': game.seed,
        'accessibility': game.accessibility.name,
        'people': list(map(person.to_db, game.people)),
        'rounds': list(map(round_service.to_db, game.rounds))
    }


def from_db(game: dict) -> Game:
    '''Convert the provided dict from the DB into a Game instance'''
    return Game(
        id=game['id'],
        name=game['name'],
        seed=game['seed'],
        accessibility=Accessibility[game['accessibility']],
        people=Group(list(map(person.person_from_db, game['people']))),
        rounds=list(map(round_service.from_db, game['rounds']))
    )


def __json(game: Game, client: str) -> dict:
    '''Convert the provided game into the structure it should provide the client'''

    return {
        'id': game.id,
        'name': game.name,
        'status': game.status.name,
        # properties that are only relevant while waiting for the game to begin
        **(__waiting_game_properties(game)
           if game.status == GameStatus.WAITING_FOR_PLAYERS
           # properties that are only relevant once the game has begun
           else __started_game_properties(game, client))
    }


def json(game: Game, client: str, initial_event_knowledge: Optional[int] = None) -> dict:
    '''
    Convert the provided game client information
    and provide information on events since on initial event
    '''

    return {
        **__json(game, client),
        # only send up the results if requested
        **({'results': event.json(game.events[initial_event_knowledge:], client)}
           if initial_event_knowledge is not None else {})
    }


def __waiting_game_properties(game: Game) -> dict:
    return {
        'accessibility': game.accessibility.name,
        'organizer': person.json(game.organizer),
        'players': list(map(person.json, [p for p in game.players if p != game.organizer])),
        'invitees': list(map(person.json, [p for p in game.invitees if p not in game.players]))
    }


def __started_game_properties(game: Game, client: str) -> dict:
    return {
        'round': round_service.json(game.active_round, client),
        'scores': game.scores
    }