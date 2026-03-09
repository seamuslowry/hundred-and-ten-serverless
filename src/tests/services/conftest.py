"""Shared test fixtures for service tests"""

import pytest
from beanie import init_beanie
from pymongo import AsyncMongoClient

from src.main.models.db.game import Game
from src.main.models.db.lobby import Lobby
from src.main.models.db.user import User


@pytest.fixture(autouse=True)
async def _init_beanie():
    """Initialize Beanie for service tests.

    Service tests call services directly (no FastAPI lifespan),
    so we need to initialize Beanie explicitly.

    This fixture is autouse=True and function-scoped, so every service test
    gets a clean database state.
    """
    client = AsyncMongoClient("mongodb://root:rootpassword@localhost:27017")
    db = client["test_db"]
    await init_beanie(database=db, document_models=[Game, Lobby, User])
    yield
    # Clean up after test
    for collection_name in await db.list_collection_names():
        await db.drop_collection(collection_name)
    await client.close()
