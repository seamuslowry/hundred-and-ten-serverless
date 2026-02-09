"""Facilitate interaction with the lobby DB"""

from bson import ObjectId
from bson.errors import InvalidId

from utils.dtos.db import SearchLobby
from utils.mappers.db import deserialize, serialize
from utils.models import Accessibility, Game, Lobby
from utils.services.game import save as save_game
from utils.services.mongo import lobby_client


def save(lobby: Lobby) -> Lobby:
    """Save the provided lobby to the DB"""
    if lobby.id is None:
        result = lobby_client.insert_one(serialize.lobby(lobby))
        lobby.id = str(result.inserted_id)
    else:
        lobby_client.update_one(
            {"_id": ObjectId(lobby.id), "type": "lobby"},
            {"$set": serialize.lobby(lobby)},
        )
    return lobby


def get(lobby_id: str) -> Lobby:
    """Retrieve the lobby with the provided ID"""
    try:
        oid = ObjectId(lobby_id)
    except InvalidId as exc:
        raise ValueError(f"No lobby found with id {lobby_id}") from exc

    result = lobby_client.find_one({"_id": oid, "type": "lobby"})

    if not result:
        raise ValueError(f"No lobby found with id {lobby_id}")

    return deserialize.lobby(result)


def search(search_lobby: SearchLobby, max_count: int) -> list[Lobby]:
    """Search for lobbies matching the provided criteria"""
    return list(
        map(
            deserialize.lobby,
            lobby_client.find(
                {
                    "type": "lobby",
                    "name": {"$regex": search_lobby["name"], "$options": "i"},
                    "$or": [
                        {"accessibility": Accessibility.PUBLIC.name},
                        {
                            "people": {
                                "$elemMatch": {
                                    "identifier": {"$eq": search_lobby["client"]}
                                }
                            }
                        },
                    ],
                }
            ).limit(max_count),
        )
    )


def start_game(lobby: Lobby) -> Game:
    """Convert a lobby to a game (starts the game)"""
    # Update the same record in DB (change type from lobby to game)
    return save_game(Game.from_lobby(lobby))
