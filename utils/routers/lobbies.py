"""
The router for lobby operations.
"""

import logging

from fastapi import APIRouter, Depends

from utils.auth import Identity, get_identity
from utils.dtos.db import SearchLobby
from utils.dtos.requests import (
    CreateLobbyRequest,
    InviteRequest,
    SearchLobbiesRequest,
)
from utils.dtos.responses import StartedGame, User, WaitingGame
from utils.mappers.client import serialize
from utils.models import Accessibility, HundredAndTenError, Lobby, Person
from utils.services import LobbyService, UserService

MIN_PLAYERS = 4


router = APIRouter(prefix="/lobbies", tags=["Lobbies"])


@router.post("/create", response_model=WaitingGame)
def create_lobby(body: CreateLobbyRequest, identity: Identity = Depends(get_identity)):
    """Create a new 110 lobby."""
    logging.info("Initiating create lobby request.")

    logging.debug("Creating lobby for %s", identity.id)

    lobby = Lobby(
        organizer=Person(identifier=identity.id),
        name=body.name,
        accessibility=Accessibility[body.accessibility],
    )

    lobby = LobbyService.save(lobby)

    logging.debug("Lobby %s created successfully", lobby.seed)

    return serialize.lobby(lobby)


@router.post("/invite/{lobby_id}", response_model=WaitingGame)
def invite_to_lobby(
    lobby_id: str, body: InviteRequest, identity: Identity = Depends(get_identity)
):
    """Invite to join a 110 lobby"""
    lobby = LobbyService.get(lobby_id)

    for invitee in body.invitees:
        lobby.invite(identity.id, Person(identifier=invitee))
    lobby = LobbyService.save(lobby)

    return serialize.lobby(lobby)


@router.post("/join/{lobby_id}", response_model=WaitingGame)
def join_lobby(lobby_id: str, identity: Identity = Depends(get_identity)):
    """Join a 110 lobby"""
    lobby = LobbyService.get(lobby_id)
    lobby.join(Person(identity.id))
    lobby = LobbyService.save(lobby)

    return serialize.lobby(lobby)


@router.post("/leave/lobby/{lobby_id}", response_model=WaitingGame)
def leave_lobby(lobby_id: str, identity: Identity = Depends(get_identity)):
    """Leave a 110 lobby"""
    lobby = LobbyService.get(lobby_id)
    lobby.leave(identity.id)
    lobby = LobbyService.save(lobby)

    return serialize.lobby(lobby)


@router.get("/lobby/{lobby_id}", response_model=WaitingGame)
def lobby_info(lobby_id: str, _identity: Identity = Depends(get_identity)):
    """Retrieve 110 lobby."""
    lobby = LobbyService.get(lobby_id)

    return serialize.lobby(lobby)


@router.get("/players/lobby/{lobby_id}", response_model=list[User])
def lobby_players(lobby_id: str, _identity: Identity = Depends(get_identity)):
    """Retrieve players in a 110 lobby."""
    lobby = LobbyService.get(lobby_id)

    people_ids = [p.identifier for p in lobby.ordered_players]

    return [serialize.user(u) for u in UserService.by_identifiers(people_ids)]


@router.post("/lobbies", response_model=list[WaitingGame])
def search_lobbies(
    body: SearchLobbiesRequest, identity: Identity = Depends(get_identity)
):
    """Search for lobbies"""
    return [
        serialize.lobby(lobby)
        for lobby in LobbyService.search(
            SearchLobby(
                name=body.searchText,
                client=identity.id,
            ),
            body.max,
        )
    ]


@router.post("/start/{lobby_id}", response_model=StartedGame)
def start_game(lobby_id: str, identity: Identity = Depends(get_identity)):
    """Start a 110 game from a lobby"""
    lobby = LobbyService.get(lobby_id)

    if identity.id != lobby.organizer.identifier:
        raise HundredAndTenError("Only the organizer can start the game")

    # Add CPU players if needed
    for num in range(len(lobby.ordered_players), MIN_PLAYERS):
        cpu_identifier = str(num + 1)
        lobby.invite(identity.id, Person(cpu_identifier, automate=True))
        lobby.join(Person(cpu_identifier, automate=True))

    # Start the game (converts lobby record to game record)
    game = LobbyService.start_game(lobby)

    return serialize.game(game, identity.id, 0)
