'''Facilitate interaction with the game DB'''
from typing import Optional

from app.mappers.db import deserialize, serialize
from app.models import Accessibility, Game, GameRole, GameStatus, Group
from app.services import person
from app.services import round as round_service
from app.services.cosmos import game_client
from app.services.mongo import m_game_client


def save(game: Game) -> Game:
    '''Save the provided game to the DB'''
    m_game_client.update_one({"id": game.id},
                             {"$set": serialize.game(game)},
                             upsert=True)
    return game


def get(game_id: str) -> Game:
    '''Retrieve the game with the provided ID'''

    result = m_game_client.find_one({"id": game_id})

    if not result:
        # TODO better error than value
        raise ValueError(f"no game found with id {game_id}")

    return deserialize.game(result)


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


def search_waiting(
        text: str,
        max_count: int,
        client: str,
        roles: Optional[list[GameRole]] = None) -> list[Game]:
    '''Retrieve the games the provided client can access that are waiting for players'''
    if roles:
        return __search_waiting_by_role(text, max_count, client, roles)
    return __search_waiting_without_client(text, max_count, client)


def search_playing(
        text: str,
        max_count: int,
        client: str,
        active: bool) -> list[Game]:
    '''
    Retrieve games that are playing rounds the client is a player on
    If active is True, will only return games where it is the client's turn to play
    '''
    if active:
        return __search_playing_by_active(text, max_count, client)
    return __search_playing_by_text(text, max_count, client)


def search_won(
        text: str,
        max_count: int,
        client: str,
        winner: bool) -> list[Game]:
    '''
    Retrieve games that are complete the client was a player on
    If winner is True, will only return games where the client's won the game
    '''
    if winner:
        return __search_won_by_winner(text, max_count, client)
    return __search_won_by_text(text, max_count, client)


def __search_won_by_winner(
        text: str,
        max_count: int,
        client: str) -> list[Game]:
    '''Retrieve games where the client's won the game'''
    return list(map(from_db, game_client.query_items(
        ('select * from game '
         'where contains(lower(game.name), lower(@text)) '
         'and game.winner = @client '
         'order by game.name '
         'offset 0 limit @max'),
        parameters=[
            {'name': '@text', 'value': text},
            {'name': '@client', 'value': client},
            {'name': '@max', 'value': max_count}
        ],
        enable_cross_partition_query=True
    )))


def __search_won_by_text(
        text: str,
        max_count: int,
        client: str) -> list[Game]:
    '''Retrieve completed games where the client was a player'''
    return list(map(from_db, game_client.query_items(
        ('select * from game '
         'where game.status=@status '
         'and contains(lower(game.name), lower(@text)) '
         'and exists(select value person from person in game.people '
         'where person.identifier = @client '
         'and array_contains(person.roles, @role)) '
         'order by game.name '
         'offset 0 limit @max'),
        parameters=[
            {
                'name': '@status',
                'value': GameStatus.WON.name
            },
            {'name': '@text', 'value': text},
            {'name': '@client', 'value': client},
            {'name': '@role', 'value': GameRole.PLAYER.name},
            {'name': '@max', 'value': max_count}
        ],
        enable_cross_partition_query=True
    )))


def __search_playing_by_active(
        text: str,
        max_count: int,
        client: str) -> list[Game]:
    '''Retrieve games where it is the client's turn to play'''
    return list(map(from_db, game_client.query_items(
        ('select * from game '
         'where not array_contains(@statuses, game.status) '
         'and contains(lower(game.name), lower(@text)) '
         'and game.activePlayer = @client '
         'order by game.name '
         'offset 0 limit @max'),
        parameters=[
            {
                'name': '@statuses',
                'value': [GameStatus.WAITING_FOR_PLAYERS.name, GameStatus.WON.name]
            },
            {'name': '@text', 'value': text},
            {'name': '@client', 'value': client},
            {'name': '@max', 'value': max_count}
        ],
        enable_cross_partition_query=True
    )))


def __search_playing_by_text(
        text: str,
        max_count: int,
        client: str) -> list[Game]:
    '''Retrieve games playing rounds where the client is a player'''
    return list(map(from_db, game_client.query_items(
        ('select * from game '
         'where not array_contains(@statuses, game.status) '
         'and contains(lower(game.name), lower(@text)) '
         'and exists(select value person from person in game.people '
         'where person.identifier = @client '
         'and array_contains(person.roles, @role)) '
         'order by game.name '
         'offset 0 limit @max'),
        parameters=[
            {
                'name': '@statuses',
                'value': [GameStatus.WAITING_FOR_PLAYERS.name, GameStatus.WON.name]
            },
            {'name': '@text', 'value': text},
            {'name': '@client', 'value': client},
            {'name': '@role', 'value': GameRole.PLAYER.name},
            {'name': '@max', 'value': max_count}
        ],
        enable_cross_partition_query=True
    )))


def __search_waiting_without_client(
        text: str, max_count: int, client: str) -> list[Game]:
    '''Retrieve the accessible games the client is not on that are waiting for players'''
    return list(map(from_db, game_client.query_items(
        ('select * from game '
         'where game.status = @status '
         'and game.accessibility = @accessibility '
         'and contains(lower(game.name), lower(@text)) '
         'and not array_contains(game.people, {"identifier": @client}, true) '
         'order by game.name '
         'offset 0 limit @max'),
        parameters=[
            {'name': '@status', 'value': GameStatus.WAITING_FOR_PLAYERS.name},
            {'name': '@accessibility', 'value': Accessibility.PUBLIC.name},
            {'name': '@text', 'value': text},
            {'name': '@client', 'value': client},
            {'name': '@max', 'value': max_count}
        ],
        enable_cross_partition_query=True
    )))


def __search_waiting_by_role(
        text: str, max_count: int, client: str, roles: list[GameRole]) -> list[Game]:
    '''
    Retrieve the games the provided client is on that are waiting for players
    '''
    return list(map(from_db, game_client.query_items(
        ('select * from game '
         'where game.status = @status '
         'and contains(lower(game.name), lower(@text)) '
         'and exists(select value person from person in game.people '
         'where person.identifier = @client '
         'and exists(select value role from role in person.roles '
         'where array_contains(@roles, role))) '
         'order by game.name '
         'offset 0 limit @max'),
        parameters=[
            {'name': '@status', 'value': GameStatus.WAITING_FOR_PLAYERS.name},
            {'name': '@text', 'value': text},
            {'name': '@client', 'value': client},
            {
                'name': '@roles',
                'value': list(map(lambda r: r.name, roles))
            },
            {'name': '@max', 'value': max_count}
        ],
        enable_cross_partition_query=True
    )))
