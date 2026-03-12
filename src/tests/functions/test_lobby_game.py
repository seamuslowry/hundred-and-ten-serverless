"""Lobby unit tests"""

from time import time

from beanie import PydanticObjectId
from fastapi.testclient import TestClient

from src.main.models.internal import GameStatus, RoundStatus
from src.tests.helpers import lobby_game


def test_lobby_info_not_an_object_id(client: TestClient):
    """Invalid lobby ID returns 422"""
    resp = client.get(
        "/players/id/lobbies/not-an-id",
        headers={"authorization": "Bearer id"},
    )
    assert 422 == resp.status_code


def test_lobby_info_not_saved_object_id(client: TestClient):
    """Invalid lobby ID returns 404"""
    resp = client.get(
        f"/players/id/lobbies/{str(PydanticObjectId())}",
        headers={"authorization": "Bearer id"},
    )
    assert 404 == resp.status_code


def test_lobby_info(client: TestClient):
    """Invalid lobby ID returns 400"""
    lobby = lobby_game(client)
    resp = client.get(
        f"/players/id/lobbies/{lobby['id']}",
        headers={"authorization": "Bearer id"},
    )

    retrieved_lobby_info = resp.json()

    assert resp.json()["id"] is not None
    assert resp.json()["name"] is not None
    assert resp.json()["organizer"] is not None
    assert [] == retrieved_lobby_info["players"]
    assert [] == retrieved_lobby_info["invitees"]


def test_create_lobby(client: TestClient):
    """New lobby can be created"""
    organizer = "organizer"
    resp = client.post(
        f"/players/{organizer}/lobbies/create",
        json={"name": "create test"},
        headers={"authorization": f"Bearer {organizer}"},
    )
    lobby = resp.json()

    assert organizer == lobby["organizer"]["identifier"]
    assert 0 == len(lobby["players"])
    assert 0 == len(lobby["invitees"])
    assert GameStatus.WAITING_FOR_PLAYERS.name == lobby["status"]


def test_organizer_invite_to_lobby(client: TestClient):
    """Organizer can invite players to a lobby"""
    invitee = "invitee"

    created_lobby = lobby_game(client)
    organizer = created_lobby["organizer"]["identifier"]

    resp = client.post(
        f"/players/{organizer}/lobbies/{created_lobby['id']}/invite",
        json={"invitees": [invitee]},
        headers={"authorization": f"Bearer {organizer}"},
    )
    invited_lobby = resp.json()

    assert created_lobby["id"] == invited_lobby["id"]
    assert 0 == len(invited_lobby["players"])
    assert 1 == len(invited_lobby["invitees"])
    assert invitee == invited_lobby["invitees"][0]["identifier"]
    assert GameStatus.WAITING_FOR_PLAYERS.name == invited_lobby["status"]


def test_invitee_invite_to_lobby(client: TestClient):
    """Invited players cannot invite players to a lobby"""
    invitee = "invitee"
    second_invitee = "second"

    created_lobby = lobby_game(client)

    organizer = created_lobby["organizer"]["identifier"]

    # invite the original
    client.post(
        f"/players/{organizer}/lobbies/{created_lobby['id']}/invite",
        json={"invitees": [invitee]},
        headers={"authorization": f"Bearer {organizer}"},
    )

    # new invitee cannot invite
    failed_invite = client.post(
        f"/players/{invitee}/lobbies/{created_lobby['id']}/invite",
        json={"invitees": [second_invitee]},
        headers={"authorization": f"Bearer {invitee}"},
    )
    assert 400 == failed_invite.status_code


def test_player_invite_to_lobby(client: TestClient):
    """Players can invite other players to a lobby"""
    invitee = "invitee"
    player = "player"

    created_lobby = lobby_game(client)

    # join as player
    client.post(
        f"/players/{player}/lobbies/{created_lobby['id']}/join",
        headers={"authorization": f"Bearer {player}"},
    )

    # new player can invite
    invite = client.post(
        f"/players/{player}/lobbies/{created_lobby['id']}/invite",
        json={"invitees": [invitee]},
        headers={"authorization": f"Bearer {player}"},
    )
    invited_lobby = invite.json()

    assert created_lobby["id"] == invited_lobby["id"]
    assert 1 == len(invited_lobby["players"])
    assert player == invited_lobby["players"][0]["identifier"]
    assert 1 == len(invited_lobby["invitees"])
    assert invitee == invited_lobby["invitees"][0]["identifier"]
    assert GameStatus.WAITING_FOR_PLAYERS.name == invited_lobby["status"]


def test_join_public_lobby(client: TestClient):
    """Any player can join a public lobby"""
    player = "player"

    created_lobby = lobby_game(client)

    resp = client.post(
        f"/players/{player}/lobbies/{created_lobby['id']}/join",
        headers={"authorization": f"Bearer {player}"},
    )
    joined_lobby = resp.json()

    assert created_lobby["id"] == joined_lobby["id"]
    assert 1 == len(joined_lobby["players"])
    assert player == joined_lobby["players"][0]["identifier"]
    assert 0 == len(joined_lobby["invitees"])
    assert GameStatus.WAITING_FOR_PLAYERS.name == joined_lobby["status"]


def test_join_private_lobby_uninvited(client: TestClient):
    """Uninvited players cannot join a private lobby"""
    organizer = "organizer"
    player = "player"

    resp = client.post(
        f"/players/{organizer}/lobbies/create",
        json={"name": "private uninvited join test", "accessibility": "PRIVATE"},
        headers={"authorization": f"Bearer {organizer}"},
    )
    created_lobby = resp.json()

    resp = client.post(
        f"/players/{player}/lobbies/{created_lobby['id']}/join",
        headers={"authorization": f"Bearer {player}"},
    )
    assert 400 == resp.status_code


def test_join_private_lobby_invited(client: TestClient):
    """Invited players can join a private lobby"""
    organizer = "organizer"
    player = "player"

    resp = client.post(
        f"/players/{organizer}/lobbies/create",
        json={"name": "private invite join test", "accessibility": "PRIVATE"},
        headers={"authorization": f"Bearer {organizer}"},
    )
    created_lobby = resp.json()

    client.post(
        f"/players/{organizer}/lobbies/{created_lobby['id']}/invite",
        json={"invitees": [player]},
        headers={"authorization": f"Bearer {organizer}"},
    )

    resp = client.post(
        f"/players/{player}/lobbies/{created_lobby['id']}/join",
        headers={"authorization": f"Bearer {player}"},
    )

    joined_lobby = resp.json()

    assert created_lobby["id"] == joined_lobby["id"]
    assert 1 == len(joined_lobby["players"])
    assert player == joined_lobby["players"][0]["identifier"]
    assert 0 == len(joined_lobby["invitees"])
    assert GameStatus.WAITING_FOR_PLAYERS.name == joined_lobby["status"]


def test_leave_lobby(client: TestClient):
    """A player can leave a lobby themselves"""
    player = "player"

    created_lobby = lobby_game(client)

    resp = client.post(
        f"/players/{player}/lobbies/{created_lobby['id']}/join",
        headers={"authorization": f"Bearer {player}"},
    )
    joined_lobby = resp.json()

    assert created_lobby["id"] == joined_lobby["id"]
    assert 1 == len(joined_lobby["players"])
    assert player == joined_lobby["players"][0]["identifier"]

    resp = client.post(
        f"/players/{player}/lobbies/{created_lobby['id']}/leave",
        headers={"authorization": f"Bearer {player}"},
    )

    left_lobby = resp.json()

    assert created_lobby["id"] == left_lobby["id"]
    assert (
        created_lobby["organizer"]["identifier"]
        == left_lobby["organizer"]["identifier"]
    )
    assert 0 == len(left_lobby["players"])
    assert GameStatus.WAITING_FOR_PLAYERS.name == left_lobby["status"]


def test_player_start_game(client: TestClient):
    """Players cannot start the game"""
    player = "player"

    created_lobby = lobby_game(client)

    client.post(
        f"/players/{player}/lobbies/{created_lobby['id']}/join",
        headers={"authorization": f"Bearer {player}"},
    )

    resp = client.post(
        f"/players/{player}/lobbies/{created_lobby['id']}/start",
        headers={"authorization": f"Bearer {player}"},
    )
    assert 400 == resp.status_code


def test_start_game(client: TestClient):
    """The organizer can start the game"""
    lobby = lobby_game(client)
    organizer = lobby["organizer"]["identifier"]

    resp = client.post(
        f"/players/{organizer}/lobbies/{lobby['id']}/start",
        headers={"authorization": f"Bearer {organizer}"},
    )

    game = resp.json()

    assert lobby["id"] != game["id"]
    assert 4 == len(game["round"]["players"])
    assert RoundStatus.BIDDING.name == game["status"]


def test_unknown_user_cannot_invite(client: TestClient):
    """A user not in the lobby cannot invite others"""
    unknown_user = "unknown_user"
    invitee = "invitee"

    created_lobby = lobby_game(client)

    # Unknown user tries to invite - should fail because they're not in the lobby
    resp = client.post(
        f"/players/{unknown_user}/lobbies/{created_lobby['id']}/invite",
        json={"invitees": [invitee]},
        headers={"authorization": f"Bearer {unknown_user}"},
    )
    assert 400 == resp.status_code


def test_unknown_player_leaves_fails(client: TestClient):
    """When an unknown player leaves, return 400 because they're not in the lobby"""
    player = "player"

    created_lobby = lobby_game(client)

    # Unrecognized player attempts to leave
    resp = client.post(
        f"/players/{player}/lobbies/{created_lobby['id']}/leave",
        headers={"authorization": f"Bearer {player}"},
    )

    assert 400 == resp.status_code


def test_organizer_leaves_fails(client: TestClient):
    """When organizer attempts to leave, prevent it"""
    player = "player"

    created_lobby = lobby_game(client)

    # Another player joins
    client.post(
        f"/players/{player}/lobbies/{created_lobby['id']}/join",
        headers={"authorization": f"Bearer {player}"},
    )
    organizer = created_lobby["organizer"]["identifier"]

    # Organizer attempts to leave
    resp = client.post(
        f"/players/{organizer}/lobbies/{created_lobby['id']}/leave",
        headers={"authorization": f"Bearer {organizer}"},
    )

    # Organizer cannot leave. Needs to delete lobby.
    assert 400 == resp.status_code


def test_search_lobbies_smoke_test(client: TestClient):
    """Can search for lobbies"""
    created_lobby = lobby_game(client)
    organizer = created_lobby["organizer"]["identifier"]

    resp = client.post(
        f"/players/{organizer}/lobbies/search",
        json={"searchText": "test"},
        headers={"authorization": f"Bearer {organizer}"},
    )

    lobbies = resp.json()
    assert len(lobbies) >= 1


def test_search_lobbies(client: TestClient):
    """Can find lobbies by name"""
    search = f"lobby{time()}"
    original_lobbies = [lobby_game(client, name=search) for _ in range(5)]

    organizer = original_lobbies[0]["organizer"]["identifier"]

    resp = client.post(
        f"/players/{organizer}/lobbies/search",
        json={"searchText": search},
        headers={"authorization": f"Bearer {organizer}"},
    )

    lobbies = resp.json()
    assert len(lobbies) == len(original_lobbies)
