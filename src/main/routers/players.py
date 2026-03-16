"""
The router for user operations.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.main.auth import Identity, get_authorized_identity
from src.main.mappers.client import serialize
from src.main.models.client.responses import User
from src.main.models.internal import User as InternalUser
from src.main.services import UserService

router = APIRouter(
    prefix="/players/{player_id}",
    tags=["Players"],
)


@router.get("/search", response_model=list[User])
async def search_users(
    search_text: Optional[str] = Query(default="", alias="searchText"),
):
    """Get users"""
    return [serialize.user(u) for u in await UserService.search(search_text or "")]


@router.put("/self", response_model=User)
async def refresh(identity: Identity = Depends(get_authorized_identity)):
    """Save the authenticated principal as a user in the DB"""
    return serialize.user(
        await UserService.save(
            InternalUser(
                player_id=identity.id,
                name=identity.name or identity.id,
                picture_url=identity.picture_url,
            )
        )
    )
