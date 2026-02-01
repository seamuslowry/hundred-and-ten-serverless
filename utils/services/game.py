"""Facilitate interaction with the game DB"""

from utils.dtos.db import SearchGame
from utils.mappers.db import deserialize, serialize
from utils.models import Accessibility, Game
from utils.services.mongo import game_client


def save(game: Game) -> Game:
    """Save the provided game to the DB"""
    game_client.update_one({"id": game.id}, {"$set": serialize.game(game)}, upsert=True)
    return game


def get(game_id: str) -> Game:
    """Retrieve the game with the provided ID"""

    result = game_client.find_one({"id": game_id})

    if not result:
        raise ValueError(f"No game found with id {game_id}")

    return deserialize.game(result)


def search(search_game: SearchGame, max_count: int) -> list[Game]:
    """Search for games matching the provided criteria"""

    active_player = search_game.get("active_player", None)
    winner = search_game.get("winner", None)
    statuses = search_game.get("statuses", None)

    # Fetch games matching basic criteria from DB
    db_games = game_client.find(
        {
            "name": {"$regex": search_game["name"], "$options": "i"},
            "$or": [
                {"accessibility": Accessibility.PUBLIC.name},
                {
                    "people": {
                        "$elemMatch": {"identifier": {"$eq": search_game["client"]}}
                    }
                },
            ],
        }
    )

    # Deserialize and filter by computed properties in memory
    results: list[Game] = []
    for db_game in db_games:
        game = deserialize.game(db_game)

        # Filter by status
        if statuses is not None and game.status.name not in statuses:
            continue

        # Filter by active player
        if active_player is not None:
            if not game.started:
                continue
            game_active_player = game.active_round.active_player
            if game_active_player is None or game_active_player.identifier != active_player:
                continue

        # Filter by winner
        if winner is not None:
            if game.winner is None or game.winner.identifier != winner:
                continue

        results.append(game)
        if len(results) >= max_count:
            break

    return results
