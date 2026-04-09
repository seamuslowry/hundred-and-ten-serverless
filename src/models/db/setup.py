"""Centralize the setup of beanie"""

import os

from beanie import init_beanie
from pymongo import AsyncMongoClient

from .game import Game, GameV0
from .lobby import Lobby, LobbyV0
from .player import Player, PlayerV0


async def initialize_odm():
    """Initialize beanie for the given client and DB"""

    connection_string = os.environ.get(
        "MongoDb", "mongodb://root:rootpassword@localhost:27017"
    )
    database_name = os.environ.get("DatabaseName", "test")

    client = AsyncMongoClient(connection_string)

    await init_beanie(
        database=client[database_name],
        document_models=[Game, GameV0, Lobby, LobbyV0, Player, PlayerV0],
    )
