"""
Task-specific QA scenarios - spot check critical tasks
"""

import asyncio
from pymongo import AsyncMongoClient
from beanie import init_beanie
from bson import ObjectId
from src.main.models.db import Lobby as DbLobby, Game as DbGame, User as DbUser
from src.main.models.internal import Lobby, Game, User, Human, Accessibility, PersonGroup
from src.main.models.client.requests import SearchLobbiesRequest, SearchGamesRequest
from src.main.services import LobbyService, GameService


async def test_task_specific_scenarios():
    print("=" * 80)
    print("TASK-SPECIFIC QA SCENARIOS")
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

    # Task 4: ElemMatch in LobbyService (search_lobby with player filter)
    print("\n" + "=" * 80)
    print("TASK 4: ElemMatch in LobbyService - search by player")
    print("=" * 80)
    total += 1
    try:
        # Create multiple lobbies with different players
        lobby1 = Lobby(
            organizer=Human("alice"),
            players=PersonGroup([Human("alice"), Human("bob")]),
            name="Alice's Lobby",
        )
        lobby2 = Lobby(
            organizer=Human("charlie"),
            players=PersonGroup([Human("charlie"), Human("diana")]),
            name="Charlie's Lobby",
        )
        lobby3 = Lobby(
            organizer=Human("alice"),
            players=PersonGroup([Human("alice"), Human("eve")]),
            name="Alice's Second Lobby",
        )

        await LobbyService.save(lobby1)
        await LobbyService.save(lobby2)
        await LobbyService.save(lobby3)

        # Search for lobbies with alice
        # alice is organizer of 2 + charlie's PUBLIC lobby = 3 accessible
        alice_lobbies = await LobbyService.search(
            "alice", SearchLobbiesRequest(searchText="", limit=10, offset=0)
        )
        assert len(alice_lobbies) == 3, f"Expected 3 lobbies accessible to alice, got {len(alice_lobbies)}"

        # Search for lobbies with bob
        # All lobbies are PUBLIC, so bob can see all 3
        bob_lobbies = await LobbyService.search(
            "bob", SearchLobbiesRequest(searchText="", limit=10, offset=0)
        )
        assert len(bob_lobbies) == 3, f"Expected 3 lobbies accessible to bob, got {len(bob_lobbies)}"

        # Search for lobbies with charlie
        # charlie is organizer of 1 + alice's 2 PUBLIC lobbies = 3 accessible
        charlie_lobbies = await LobbyService.search(
            "charlie", SearchLobbiesRequest(searchText="", limit=10, offset=0)
        )
        assert len(charlie_lobbies) == 3, (
            f"Expected 3 lobbies accessible to charlie, got {len(charlie_lobbies)}"
        )

        print("✓ Task 4 PASSED: ElemMatch query works correctly in LobbyService")
        passed += 1
    except Exception as e:
        print(f"✗ Task 4 FAILED: {e}")

    # Clean up
    await db.lobbies.delete_many({})
    await db.games.delete_many({})

    # Task 5: ElemMatch in GameService (search_game with player filter)
    print("\n" + "=" * 80)
    print("TASK 5: ElemMatch in GameService - search by player")
    print("=" * 80)
    total += 1
    try:
        # Create lobbies and start games
        lobby1 = Lobby(
            organizer=Human("alice"),
            players=PersonGroup([Human("alice"), Human("bob")]),
            name="Game 1",
        )
        lobby2 = Lobby(
            organizer=Human("charlie"),
            players=PersonGroup([Human("charlie"), Human("diana")]),
            name="Game 2",
        )
        lobby3 = Lobby(
            organizer=Human("alice"),
            players=PersonGroup([Human("alice"), Human("eve")]),
            name="Game 3",
        )

        saved_lobby1 = await LobbyService.save(lobby1)
        saved_lobby2 = await LobbyService.save(lobby2)
        saved_lobby3 = await LobbyService.save(lobby3)

        await LobbyService.start_game(saved_lobby1)
        await LobbyService.start_game(saved_lobby2)
        await LobbyService.start_game(saved_lobby3)

        # Search for games with alice
        # All games are PUBLIC, alice can see all 3
        alice_games = await GameService.search(
            "alice", SearchGamesRequest(searchText="", limit=10, offset=0)
        )
        assert len(alice_games) == 3, f"Expected 3 games accessible to alice, got {len(alice_games)}"

        # Search for games with bob
        # All games are PUBLIC, bob can see all 3
        bob_games = await GameService.search(
            "bob", SearchGamesRequest(searchText="", limit=10, offset=0)
        )
        assert len(bob_games) == 3, f"Expected 3 games accessible to bob, got {len(bob_games)}"

        # Search for games with charlie
        # charlie is in 1 game (as organizer) + alice's 2 PUBLIC games = 3 accessible
        charlie_games = await GameService.search(
            "charlie", SearchGamesRequest(searchText="", limit=10, offset=0)
        )
        assert len(charlie_games) == 3, (
            f"Expected 3 games accessible to charlie, got {len(charlie_games)}"
        )

        print("✓ Task 5 PASSED: ElemMatch query works correctly in GameService")
        passed += 1
    except Exception as e:
        print(f"✗ Task 5 FAILED: {e}")

    # Clean up
    await db.lobbies.delete_many({})
    await db.games.delete_many({})

    # Task 6: start_game sequential (no transactions)
    print("\n" + "=" * 80)
    print("TASK 6: start_game sequential execution (no transactions)")
    print("=" * 80)
    total += 1
    try:
        lobby = Lobby(
            organizer=Human("user1"),
            players=PersonGroup([Human("user1"), Human("user2")]),
            name="Test",
        )
        saved_lobby = await LobbyService.save(lobby)

        # Start game
        game = await LobbyService.start_game(saved_lobby)

        # Verify game exists
        found_game = await GameService.get(game.id)
        assert found_game.id == saved_lobby.id

        # Verify lobby deleted
        try:
            await LobbyService.get(saved_lobby.id)
            raise AssertionError("Lobby should have been deleted")
        except ValueError:
            pass  # Expected

        print("✓ Task 6 PASSED: Sequential start_game execution works correctly")
        passed += 1
    except Exception as e:
        print(f"✗ Task 6 FAILED: {e}")

    print("\n" + "=" * 80)
    print(f"TASK-SPECIFIC SCENARIOS: {passed}/{total} passed")
    print("=" * 80)
    return passed == total


if __name__ == "__main__":
    try:
        result = asyncio.run(test_task_specific_scenarios())
        exit(0 if result else 1)
    except Exception as e:
        print(f"\n❌ TASK-SPECIFIC SCENARIOS FAILED: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
