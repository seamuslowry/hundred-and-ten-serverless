"""
Integration test for lobby-to-game workflow.
Tests the complete flow: create lobby -> start game -> verify lobby deleted -> verify game exists
"""

import asyncio
from beanie import init_beanie
from pymongo import AsyncMongoClient
from src.main.models.db import Lobby as DbLobby, Game as DbGame, User as DbUser
from src.main.models.internal import Lobby, Game, User, Human, Accessibility, PersonGroup
from src.main.services import LobbyService, GameService


async def test_lobby_to_game_workflow():
    print("=" * 80)
    print("INTEGRATION TEST: Lobby → Game Workflow")
    print("=" * 80)

    # Initialize beanie
    print("[1] Connecting to MongoDB...")
    client = AsyncMongoClient("mongodb://root:rootpassword@localhost:27017")
    db = client.test_db
    
    print("[2] Initializing Beanie...")
    await init_beanie(database=db, document_models=[DbLobby, DbGame, DbUser])

    # Clean up
    print("[3] Cleaning up existing data...")
    await db.lobbies.delete_many({})
    await db.games.delete_many({})
    print(f"    - Deleted all lobbies and games")

    # Create test lobby
    print("\n[4] Creating test lobby...")
    organizer = Human("user1")
    player2 = Human("user2")
    lobby = Lobby(
        organizer=organizer,
        players=PersonGroup([organizer, player2]),
        name="Test Lobby",
        accessibility=Accessibility.PUBLIC
    )

    # Save lobby
    saved_lobby = await LobbyService.save(lobby)
    print(f"    ✓ Lobby created: {saved_lobby.id}")

    # Verify lobby exists
    print("\n[5] Verifying lobby retrieval...")
    found_lobby = await LobbyService.get(saved_lobby.id)
    assert found_lobby.id == saved_lobby.id
    assert len(found_lobby.players) == 2
    print(f"    ✓ Lobby retrieval works")
    print(f"    ✓ Players count: {len(found_lobby.players)}")

    # Start game (converts lobby to game, deletes lobby)
    print("\n[6] Starting game (sequential: create game, then delete lobby)...")
    game = await LobbyService.start_game(saved_lobby)
    print(f"    ✓ Game created: {game.id}")

    # Verify lobby is deleted
    print("\n[7] Verifying lobby deletion...")
    try:
        await LobbyService.get(saved_lobby.id)
        print("    ✗ ERROR: Lobby still exists after game start!")
        return False
    except ValueError as e:
        print(f"    ✓ Lobby deleted after game start (ValueError: {e})")

    # Verify game exists with same ID
    print("\n[8] Verifying game exists with correct ID...")
    found_game = await GameService.get(game.id)
    assert found_game.id == saved_lobby.id  # Game should have lobby's ID
    print(f"    ✓ Game ID matches lobby ID: {found_game.id}")

    # Verify player data preserved
    print("\n[9] Verifying player data preservation...")
    assert len(found_game.players) == 2
    assert any(p.identifier == "user1" for p in found_game.players)
    assert any(p.identifier == "user2" for p in found_game.players)
    print(f"    ✓ Player data preserved in game")
    print(f"    ✓ Players: {[p.identifier for p in found_game.players]}")

    # Verify ElemMatch query works (search game by player)
    print("\n[10] Testing ElemMatch query (search by player)...")
    from src.main.models.client.requests import SearchGamesRequest

    games = await GameService.search("user1", SearchGamesRequest(searchText="", limit=10, offset=0))
    assert len(games) > 0, "Search should return at least one game"
    assert any(g.id == game.id for g in games), "Search should find the created game"
    print(f"    ✓ ElemMatch query found game by player ID")
    print(f"    ✓ Games found: {len(games)}")

    # Test search with player filter
    print("\n[11] Testing search with different player...")
    games_user2 = await GameService.search(
        "user2", SearchGamesRequest(searchText="", limit=10, offset=0)
    )
    assert len(games_user2) > 0, "Search for user2 should return at least one game"
    assert any(g.id == game.id for g in games_user2), "Search should find the same game for user2"
    print(f"    ✓ Search works for both players")

    # Test search with text filter
    print("\n[12] Testing search with text filter...")
    games_text = await GameService.search(
        "user1", SearchGamesRequest(searchText="Test", limit=10, offset=0)
    )
    assert len(games_text) > 0, "Text search should return results"
    print(f"    ✓ Text search works: {len(games_text)} games found")

    print("\n" + "=" * 80)
    print("✅ INTEGRATION TEST PASSED - All verifications successful")
    print("=" * 80)
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(test_lobby_to_game_workflow())
        exit(0 if result else 1)
    except Exception as e:
        print(f"\n❌ INTEGRATION TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
