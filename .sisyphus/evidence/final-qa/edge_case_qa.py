"""
Edge case testing for beanie migration
"""

import asyncio
from pymongo import AsyncMongoClient
from beanie import init_beanie
from bson import ObjectId
from src.main.models.db import Lobby as DbLobby, Game as DbGame, User as DbUser
from src.main.models.internal import Lobby, Game, User, Human, Accessibility, PersonGroup
from src.main.models.client.requests import SearchLobbiesRequest, SearchGamesRequest
from src.main.services import LobbyService, GameService


async def test_edge_cases():
    print("=" * 80)
    print("EDGE CASE TESTING")
    print("=" * 80)

    # Initialize beanie
    print("\n[1] Initializing Beanie...")
    client = AsyncMongoClient("mongodb://root:rootpassword@localhost:27017")
    db = client.test_db
    await init_beanie(database=db, document_models=[DbLobby, DbGame, DbUser])

    # Clean up
    await db.lobbies.delete_many({})
    await db.games.delete_many({})

    passed = 0
    total = 0

    # Edge case 1: Empty search results
    print("\n" + "=" * 80)
    print("EDGE CASE 1: Empty search results")
    print("=" * 80)
    total += 1
    try:
        # Search with no lobbies
        lobbies = await LobbyService.search(
            "nonexistent", SearchLobbiesRequest(searchText="", limit=10, offset=0)
        )
        assert len(lobbies) == 0, f"Expected 0 lobbies, got {len(lobbies)}"

        # Search with no games
        games = await GameService.search(
            "nonexistent", SearchGamesRequest(searchText="", limit=10, offset=0)
        )
        assert len(games) == 0, f"Expected 0 games, got {len(games)}"

        print("✓ PASSED: Empty search results handled correctly")
        passed += 1
    except Exception as e:
        print(f"✗ FAILED: {e}")

    # Edge case 2: Non-existent IDs (should raise ValueError)
    print("\n" + "=" * 80)
    print("EDGE CASE 2: Non-existent IDs raise ValueError")
    print("=" * 80)
    total += 1
    try:
        # Try to get non-existent lobby
        fake_id = str(ObjectId())
        try:
            await LobbyService.get(fake_id)
            raise AssertionError("Should have raised ValueError for non-existent lobby")
        except ValueError as e:
            assert "No lobby found" in str(e)

        # Try to get non-existent game
        try:
            await GameService.get(fake_id)
            raise AssertionError("Should have raised ValueError for non-existent game")
        except ValueError as e:
            assert "No game found" in str(e)

        print("✓ PASSED: Non-existent IDs raise ValueError correctly")
        passed += 1
    except Exception as e:
        print(f"✗ FAILED: {e}")

    # Edge case 3: Minimum player count validation (start_game with < 2 players should fail)
    print("\n" + "=" * 80)
    print("EDGE CASE 3: start_game requires minimum 2 players")
    print("=" * 80)
    total += 1
    try:
        # Create lobby with only organizer (1 player)
        lobby = Lobby(organizer=Human("solo"), name="Solo Lobby")
        saved_lobby = await LobbyService.save(lobby)

        # Try to start game with 1 player
        try:
            await LobbyService.start_game(saved_lobby)
            raise AssertionError("Should have raised ValueError for < 2 players")
        except ValueError as e:
            assert "at least 2 players" in str(e) or "minimum" in str(e).lower()

        # Verify lobby still exists (game not created)
        found_lobby = await LobbyService.get(saved_lobby.id)
        assert found_lobby.id == saved_lobby.id

        print("✓ PASSED: Minimum player validation works correctly")
        passed += 1
    except Exception as e:
        print(f"✗ FAILED: {e}")

    # Edge case 4: Search with text filter
    print("\n" + "=" * 80)
    print("EDGE CASE 4: Search with text filter")
    print("=" * 80)
    total += 1
    try:
        await db.lobbies.delete_many({})

        # Create lobbies with specific names
        lobby1 = Lobby(organizer=Human("user1"), name="Alpha Lobby")
        lobby2 = Lobby(organizer=Human("user2"), name="Beta Lobby")
        lobby3 = Lobby(organizer=Human("user3"), name="Alpha Beta Lobby")

        await LobbyService.save(lobby1)
        await LobbyService.save(lobby2)
        await LobbyService.save(lobby3)

        # Search for "Alpha"
        alpha_lobbies = await LobbyService.search(
            "user1", SearchLobbiesRequest(searchText="Alpha", limit=10, offset=0)
        )
        assert len(alpha_lobbies) == 2, f"Expected 2 lobbies with 'Alpha', got {len(alpha_lobbies)}"

        # Search for "Beta"
        beta_lobbies = await LobbyService.search(
            "user1", SearchLobbiesRequest(searchText="Beta", limit=10, offset=0)
        )
        assert len(beta_lobbies) == 2, f"Expected 2 lobbies with 'Beta', got {len(beta_lobbies)}"

        # Search for non-matching text
        none_lobbies = await LobbyService.search(
            "user1", SearchLobbiesRequest(searchText="Gamma", limit=10, offset=0)
        )
        assert len(none_lobbies) == 0, f"Expected 0 lobbies with 'Gamma', got {len(none_lobbies)}"

        print("✓ PASSED: Text filter works correctly")
        passed += 1
    except Exception as e:
        print(f"✗ FAILED: {e}")

    # Edge case 5: Pagination (limit/offset)
    print("\n" + "=" * 80)
    print("EDGE CASE 5: Pagination with limit/offset")
    print("=" * 80)
    total += 1
    try:
        await db.lobbies.delete_many({})

        # Create 5 lobbies
        for i in range(5):
            lobby = Lobby(organizer=Human(f"user{i}"), name=f"Lobby {i}")
            await LobbyService.save(lobby)

        # Get first 2
        page1 = await LobbyService.search(
            "user0", SearchLobbiesRequest(searchText="", limit=2, offset=0)
        )
        assert len(page1) == 2, f"Expected 2 lobbies, got {len(page1)}"

        # Get next 2
        page2 = await LobbyService.search(
            "user0", SearchLobbiesRequest(searchText="", limit=2, offset=2)
        )
        assert len(page2) == 2, f"Expected 2 lobbies, got {len(page2)}"

        # Get last 1
        page3 = await LobbyService.search(
            "user0", SearchLobbiesRequest(searchText="", limit=2, offset=4)
        )
        assert len(page3) == 1, f"Expected 1 lobby, got {len(page3)}"

        # Verify no overlap
        page1_ids = {l.id for l in page1}
        page2_ids = {l.id for l in page2}
        page3_ids = {l.id for l in page3}
        assert len(page1_ids & page2_ids) == 0, "Pages 1 and 2 should not overlap"
        assert len(page1_ids & page3_ids) == 0, "Pages 1 and 3 should not overlap"
        assert len(page2_ids & page3_ids) == 0, "Pages 2 and 3 should not overlap"

        print("✓ PASSED: Pagination works correctly")
        passed += 1
    except Exception as e:
        print(f"✗ FAILED: {e}")

    print("\n" + "=" * 80)
    print(f"EDGE CASES: {passed}/{total} passed")
    print("=" * 80)
    return passed == total


if __name__ == "__main__":
    try:
        result = asyncio.run(test_edge_cases())
        exit(0 if result else 1)
    except Exception as e:
        print(f"\n❌ EDGE CASE TESTING FAILED: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
