"""Facilitate interaction with the game DB"""

from bson import ObjectId
from bson.errors import InvalidId

from utils.mappers.db import deserialize, serialize
from utils.models import Accessibility, Game
from utils.models.db import SearchGame
from utils.services.mongo import game_client


def save(game: Game) -> Game:
    """Save the provided game to the DB"""
    game_client.update_one(
        {"_id": ObjectId(game.id)},
        {"$set": serialize.game(game).model_dump(by_alias=True, exclude={"id"})},
    )
    return game


def get(game_id: str) -> Game:
    """Retrieve the game with the provided ID"""
    try:
        oid = ObjectId(game_id)
    except InvalidId as exc:
        raise ValueError(f"No game found with id {game_id}") from exc

    result = game_client.find_one({"_id": oid, "type": "game"})

    if not result:
        raise ValueError(f"No game found with id {game_id}")

    return deserialize.game(result)


def search(search_game: SearchGame, max_count: int) -> list[Game]:
    """Search for games matching the provided criteria"""
    return list(
        map(
            deserialize.game,
            game_client.find(
                {
                    "type": "game",
                    "name": {"$regex": search_game.name, "$options": "i"},
                    "$or": [
                        {"accessibility": Accessibility.PUBLIC.name},
                        {
                            "people": {
                                "$elemMatch": {
                                    "identifier": {"$eq": search_game.client}
                                }
                            }
                        },
                    ],
                    **(
                        {"active_player": search_game.active_player}
                        if search_game.active_player is not None
                        else {}
                    ),
                    **(
                        {"winner": search_game.winner}
                        if search_game.winner is not None
                        else {}
                    ),
                    **(
                        {"status": {"$in": search_game.statuses}}
                        if search_game.statuses is not None
                        else {}
                    ),
                }
            ).limit(max_count),
        )
    )
