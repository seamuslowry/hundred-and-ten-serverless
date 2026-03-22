"""
The router for player operations.
"""

from fastapi import APIRouter, Depends

from src.main.auth import Identity, get_authorized_identity_for_path_player
from src.main.mappers.client import serialize
from src.main.models.client.requests import SearchPlayersRequest
from src.main.models.client.responses import Player
from src.main.models.internal import Player as InternalPlayer
from src.main.services import PlayerService

router = APIRouter(
    prefix="/players",
    tags=["Players"],
)


@router.get("/{player_id}", response_model=Player)
async def get_player(
    player_id: str,
):
    """Get player"""
    return serialize.player(await PlayerService.by_player_id(player_id))


@router.put("/{player_id}", response_model=Player)
async def refresh(
    identity: Identity = Depends(get_authorized_identity_for_path_player),
):
    """Save the authenticated principal as a player in the DB"""
    return serialize.player(
        await PlayerService.save(
            InternalPlayer(
                player_id=identity.id,
                name=identity.name or identity.id,
                picture_url=identity.picture_url,
            )
        )
    )


@router.post("/search", response_model=list[Player])
async def search_players(
    body: SearchPlayersRequest,
):
    """Search players"""
    return [serialize.player(u) for u in await PlayerService.search(body)]
