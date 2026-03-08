"""
The router for user operations.
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.main.mappers.client import deserialize, serialize
from src.main.models.client.requests import UpdateUserRequest
from src.main.models.client.responses import User
from src.main.services import UserService

router = APIRouter(
    prefix="/players/{player_id}",
    tags=["Players"],
)


@router.get("/search", response_model=list[User])
def search_users(
    search_text: Optional[str] = Query(default="", alias="searchText"),
):
    """Get users"""
    return [serialize.user(u) for u in UserService.search(search_text or "")]


@router.put("", response_model=User)
def put_user(player_id: str, body: UpdateUserRequest):
    """Update the user (overwrite)"""
    provided_user = deserialize.user(player_id, body)

    return serialize.user(UserService.save(provided_user))


@router.post("", response_model=User)
def post_user(player_id, body: UpdateUserRequest):
    """Create the user (only if not exists)"""
    existing_user = UserService.by_identifier(player_id)
    provided_user = deserialize.user(player_id, body)

    save_user = provided_user if not existing_user else existing_user

    return serialize.user(UserService.save(save_user))
