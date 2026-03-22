"""
The router for player operations.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.main.auth import Identity, get_authorized_identity
from src.main.mappers.client import serialize
from src.main.models.client.responses import Player
from src.main.models.internal import Player as InternalPlayer
from src.main.services import PlayerService

router = APIRouter(
    prefix="/players/{player_id}",
    tags=["Players"],
)


@router.get("", response_model=list[Player])
async def search_players(
    search_text: Optional[str] = Query(default="", alias="searchText"),
):
    """Get players"""
    return [serialize.player(u) for u in await PlayerService.search(search_text or "")]


@router.put("", response_model=Player)
async def refresh(identity: Identity = Depends(get_authorized_identity)):
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
