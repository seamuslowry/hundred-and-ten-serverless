"""
The router for lobby operations.
"""

import logging

from fastapi import APIRouter

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


router = APIRouter(
    prefix="/players/{player_id}/lobbies",
    tags=["Lobbies"],
)


@router.get("/{lobby_id}", response_model=WaitingGame)
def lobby_info(lobby_id: str):
    """Retrieve 110 lobby."""
    lobby = LobbyService.get(lobby_id)

    return serialize.lobby(lobby)


@router.get("/{lobby_id}/players", response_model=list[User])
def lobby_players(lobby_id: str):
    """Retrieve players in a 110 lobby."""
    lobby = LobbyService.get(lobby_id)

    people_ids = [p.identifier for p in lobby.ordered_players]

    return [serialize.user(u) for u in UserService.by_identifiers(people_ids)]


@router.post("/search", response_model=list[WaitingGame])
def search_lobbies(player_id: str, body: SearchLobbiesRequest):
    """Search for lobbies"""
    return [
        serialize.lobby(lobby)
        for lobby in LobbyService.search(
            SearchLobby(
                name=body.searchText,
                client=player_id,
            ),
            body.max,
        )
    ]


@router.post("/create", response_model=WaitingGame)
def create_lobby(player_id: str, body: CreateLobbyRequest):
    """Create a new 110 lobby."""
    logging.info("Initiating create lobby request.")

    logging.debug("Creating lobby for %s", player_id)

    lobby = Lobby(
        organizer=Person(identifier=player_id),
        name=body.name,
        accessibility=Accessibility[body.accessibility],
    )

    lobby = LobbyService.save(lobby)

    logging.debug("Lobby %s created successfully", lobby.seed)

    return serialize.lobby(lobby)


@router.post("/{lobby_id}/invite", response_model=WaitingGame)
def invite_to_lobby(player_id: str, lobby_id: str, body: InviteRequest):
    """Invite to join a 110 lobby"""
    lobby = LobbyService.get(lobby_id)

    for invitee in body.invitees:
        lobby.invite(player_id, Person(identifier=invitee))
    lobby = LobbyService.save(lobby)

    return serialize.lobby(lobby)


@router.post("/{lobby_id}/join", response_model=WaitingGame)
def join_lobby(player_id: str, lobby_id: str):
    """Join a 110 lobby"""
    lobby = LobbyService.get(lobby_id)
    lobby.join(Person(player_id))
    lobby = LobbyService.save(lobby)

    return serialize.lobby(lobby)


@router.post("/{lobby_id}/leave", response_model=WaitingGame)
def leave_lobby(player_id: str, lobby_id: str):
    """Leave a 110 lobby"""
    lobby = LobbyService.get(lobby_id)
    lobby.leave(player_id)
    lobby = LobbyService.save(lobby)

    return serialize.lobby(lobby)


@router.post("/{lobby_id}/start", response_model=StartedGame)
def start_game(player_id: str, lobby_id: str):
    """Start a 110 game from a lobby"""
    lobby = LobbyService.get(lobby_id)

    if player_id != lobby.organizer.identifier:
        raise HundredAndTenError("Only the organizer can start the game")

    # Add CPU players if needed
    for num in range(len(lobby.ordered_players), MIN_PLAYERS):
        cpu_identifier = str(num + 1)
        lobby.invite(player_id, Person(cpu_identifier, automate=True))
        lobby.join(Person(cpu_identifier, automate=True))

    # Start the game (converts lobby record to game record)
    game = LobbyService.start_game(lobby)

    return serialize.game(game, player_id, 0)
