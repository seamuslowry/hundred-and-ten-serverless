"""
The router for lobby operations.
"""

import logging

from beanie import PydanticObjectId
from fastapi import APIRouter

from src.main.mappers.client import serialize
from src.main.models.client.requests import (
    CreateLobbyRequest,
    InviteRequest,
    SearchLobbiesRequest,
)
from src.main.models.client.responses import Player, StartedGame, WaitingGame
from src.main.models.internal import (
    Accessibility,
    Human,
    HundredAndTenError,
    Lobby,
    NaiveCpu,
)
from src.main.services import LobbyService, UserService

MIN_PLAYERS = 4


router = APIRouter(
    prefix="/players/{player_id}/lobbies",
    tags=["Lobbies"],
)


@router.get("/{lobby_id}", response_model=WaitingGame)
async def lobby_info(lobby_id: PydanticObjectId):
    """Retrieve 110 lobby."""
    lobby = await LobbyService.get(lobby_id)

    return serialize.lobby(lobby)


@router.get("/{lobby_id}/players", response_model=list[Player])
async def lobby_players(lobby_id: PydanticObjectId):
    """Retrieve players in a 110 lobby."""
    lobby = await LobbyService.get(lobby_id)

    people_ids = [p.identifier for p in lobby.ordered_players]

    return [serialize.player(u) for u in await UserService.by_identifiers(people_ids)]


@router.post("/search", response_model=list[WaitingGame])
async def search_lobbies(player_id: str, body: SearchLobbiesRequest):
    """Search for lobbies"""
    return [
        serialize.lobby(lobby)
        for lobby in await LobbyService.search(
            player_id,
            body,
        )
    ]


@router.post("/create", response_model=WaitingGame)
async def create_lobby(player_id: str, body: CreateLobbyRequest):
    """Create a new 110 lobby."""
    logging.info("Initiating create lobby request.")

    logging.debug("Creating lobby for %s", player_id)

    lobby = Lobby(
        organizer=Human(identifier=player_id),
        name=body.name,
        accessibility=Accessibility[body.accessibility],
    )

    lobby = await LobbyService.save(lobby)

    logging.debug("Lobby %s created successfully", lobby.seed)

    return serialize.lobby(lobby)


@router.post("/{lobby_id}/invite", response_model=WaitingGame)
async def invite_to_lobby(
    player_id: str, lobby_id: PydanticObjectId, body: InviteRequest
):
    """Invite to join a 110 lobby"""
    lobby = await LobbyService.get(lobby_id)

    for invitee in body.invitees:
        lobby.invite(player_id, Human(identifier=invitee))
    lobby = await LobbyService.save(lobby)

    return serialize.lobby(lobby)


@router.post("/{lobby_id}/join", response_model=WaitingGame)
async def join_lobby(player_id: str, lobby_id: PydanticObjectId):
    """Join a 110 lobby"""
    lobby = await LobbyService.get(lobby_id)
    lobby.join(Human(player_id))
    lobby = await LobbyService.save(lobby)

    return serialize.lobby(lobby)


@router.post("/{lobby_id}/leave", response_model=WaitingGame)
async def leave_lobby(player_id: str, lobby_id: PydanticObjectId):
    """Leave a 110 lobby"""
    lobby = await LobbyService.get(lobby_id)
    lobby.leave(player_id)
    lobby = await LobbyService.save(lobby)

    return serialize.lobby(lobby)


@router.post("/{lobby_id}/start", response_model=StartedGame)
async def start_game(player_id: str, lobby_id: PydanticObjectId):
    """Start a 110 game from a lobby"""
    lobby = await LobbyService.get(lobby_id)

    if player_id != lobby.organizer.identifier:
        raise HundredAndTenError("Only the organizer can start the game")

    # Add CPU players if needed
    for num in range(len(lobby.ordered_players), MIN_PLAYERS):
        cpu_identifier = str(num + 1)
        lobby.invite(player_id, NaiveCpu(cpu_identifier))
        lobby.join(NaiveCpu(cpu_identifier))

    # Start the game (converts lobby record to game record)
    game = await LobbyService.start_game(lobby)

    return serialize.game(game, player_id, 0)
