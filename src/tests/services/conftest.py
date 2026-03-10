"""Shared test fixtures for service tests"""

import pytest
from pymongo import AsyncMongoClient

from src.main.models.db.setup import init_beanie_for_client


@pytest.fixture(autouse=True)
async def _init_beanie():
    """Initialize Beanie for service tests.

    Service tests call services directly (no FastAPI lifespan),
    so we need to initialize Beanie explicitly.

    This fixture is autouse=True and function-scoped, so every service test
    gets a clean database state.
    """
    client = AsyncMongoClient("mongodb://root:rootpassword@localhost:27017")
    await init_beanie_for_client(client, "test_db")
    yield
