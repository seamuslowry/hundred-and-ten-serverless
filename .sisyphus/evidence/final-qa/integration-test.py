#!/usr/bin/env python3
"""
Integration Test: Create Lobby → Start Game
Tests: serialize + ElemMatch + transaction working together
"""

import asyncio
import sys

sys.path.insert(0, "/home/seamus/git/hundred-and-ten-serverless")

from beanie import init_beanie
from pymongo import AsyncMongoClient

from src.main.models.db.game import Game as DbGame
from src.main.models.db.lobby import Lobby as DbLobby, Accessibility
from src.main.models.db.user import User as DbUser
from src.main.models.db.player import HumanPlayer
from src.main.services.lobby import LobbyService
from src.main.services.game import GameService
from src.main.models.client.requests import SearchGamesRequest


async def main():
    # Initialize beanie
    client = AsyncMongoClient("mongodb://localhost:27017/?replicaSet=rs0")
    db = client["test_db"]
    await init_beanie(database=db, document_models=[DbGame, DbLobby, DbUser])

    print("=== INTEGRATION TEST: Create Lobby → Start Game ===\n")

    # Step 1: Create lobby with 2 players using the existing test pattern
    print("STEP 1: Create lobby with 2 players")
    player1 = HumanPlayer(identifier="player1")
    player2 = HumanPlayer(identifier="player2")

    # Create a DbLobby directly (like the service does)
    db_lobby = DbLobby(
        name="Integration Test Lobby",
        accessibility=Accessibility.PUBLIC,
        organizer=player1,
        players=[player1, player2],
        invitees=[],
    )
    await db_lobby.save()

    lobby_id = str(db_lobby.id)
    print(f"✓ Created lobby: {lobby_id}")
    print(f"  - Organizer: {db_lobby.organizer.identifier}")
    print(f"  - Players: {[p.identifier for p in db_lobby.players]}\n")

    # Get internal lobby representation
    internal_lobby = await LobbyService.get(lobby_id)

    # Step 2: Start game (uses transaction)
    print("STEP 2: Start game (transaction: delete lobby + create game)")
    game = await LobbyService.start_game(internal_lobby)
    game_id = game.id
    print(f"✓ Game started: {game_id}")
    print(f"  - Players: {[p.identifier for p in game.players]}\n")

    # Step 3: Verify lobby was deleted
    print("STEP 3: Verify lobby deleted")
    try:
        await LobbyService.get(lobby_id)
        print("✗ FAIL: Lobby still exists!")
        return False
    except:
        print("✓ Lobby deleted\n")

    # Step 4: Query game by player ID (uses ElemMatch)
    print("STEP 4: Query game by player ID (ElemMatch)")
    search_request = SearchGamesRequest(searchText="")
    games = await GameService.search("player1", search_request)
    if not games:
        print("✗ FAIL: No games found for player1")
        return False
    print(f"✓ Found {len(games)} game(s) for player1")

    found_game = games[0]
    if found_game.id != game_id:
        print(f"✗ FAIL: Wrong game returned (expected {game_id}, got {found_game.id})")
        return False
    print(f"  - Game ID matches: {found_game.id}\n")

    # Step 5: Verify both players present
    print("STEP 5: Verify both players present in game")
    player_ids = [p.identifier for p in found_game.players]
    if "player1" not in player_ids or "player2" not in player_ids:
        print(f"✗ FAIL: Missing players. Found: {player_ids}")
        return False
    print(f"✓ Both players present: {player_ids}\n")

    # Cleanup
    await db.drop_collection("games")
    await db.drop_collection("lobbies")
    await client.close()

    print("=== INTEGRATION TEST: PASS ===")
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
