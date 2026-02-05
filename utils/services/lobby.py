"""Facilitate interaction with the lobby DB"""

from utils.dtos.db import SearchLobby
from utils.mappers.db import deserialize, serialize
from utils.models import Accessibility, Game, Lobby
from utils.services.mongo import game_client, lobby_client


def save(lobby: Lobby) -> Lobby:
    """Save the provided lobby to the DB"""
    lobby_client.update_one({"id": lobby.id}, {"$set": serialize.lobby(lobby)}, upsert=True)
    return lobby


def get(lobby_id: str) -> Lobby:
    """Retrieve the lobby with the provided ID"""
    result = lobby_client.find_one({"id": lobby_id, "type": "lobby"})

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
    game = Game.from_lobby(lobby)
    # Update the same record in DB (change type from lobby to game)
    game_client.update_one({"id": game.id}, {"$set": serialize.game(game)})
    return game
