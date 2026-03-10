"""Centralize the setup of beanie"""

from beanie import init_beanie
from pymongo import AsyncMongoClient

from .game import Game, GameV0
from .lobby import Lobby, LobbyV0
from .user import User, UserV0


async def init_beanie_for_client(client: AsyncMongoClient, db_name: str):
    """Initialize beanie for the given client and DB"""
    await init_beanie(
        database=client[db_name],
        document_models=[Game, GameV0, Lobby, LobbyV0, User, UserV0],
    )
