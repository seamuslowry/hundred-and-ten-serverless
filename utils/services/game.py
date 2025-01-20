'''Facilitate interaction with the game DB'''

from utils.dtos.db import SearchGame
from utils.mappers.db import deserialize, serialize
from utils.models import Accessibility, Game
from utils.services.mongo import game_client


def save(game: Game) -> Game:
    '''Save the provided game to the DB'''
    game_client.update_one({"id": game.id},
                           {"$set": serialize.game(game)},
                           upsert=True)
    return game


def get(game_id: str) -> Game:
    '''Retrieve the game with the provided ID'''

    result = game_client.find_one({"id": game_id})

    if not result:
        raise ValueError(f"No game found with id {game_id}")

    return deserialize.game(result)


def search(
    search_game: SearchGame,
    max_count: int
) -> list[Game]:
    '''Search for games matching the provided criteria'''

    active_player = search_game.get('active_player', None)
    winner = search_game.get('winner', None)
    statuses = search_game.get('statuses', None)

    return list(map(deserialize.game,
                    game_client.find({
                        'name': {'$regex': search_game['name'], '$options': 'i'},
                        '$or': [
                            {
                                'accessibility': Accessibility.PUBLIC.name
                            },
                            {
                                'people': {
                                    '$elemMatch': {
                                        'identifier': {'$eq': search_game['client']}
                                    }
                                }
                            }
                        ],
                        **({'active_player': active_player} if active_player is not None else {}),
                        **({'winner': winner} if winner is not None else {}),
                        **({'status': {'$in': statuses}} if statuses is not None else {})
                    }).limit(max_count)))
