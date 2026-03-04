"""
The router for user operations.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from utils.auth import Identity, get_identity
from utils.dtos.requests import UpdateUserRequest
from utils.dtos.responses import User
from utils.mappers.client import deserialize, serialize
from utils.services import UserService

router = APIRouter(prefix="/players", tags=["Players"])


@router.get("/search", response_model=list[User])
def search_users(
    search_text: Optional[str] = Query(default="", alias="searchText"),
):
    """Get users"""
    return [serialize.user(u) for u in UserService.search(search_text or "")]


@router.put("/self", response_model=User)
def put_self(body: UpdateUserRequest, identity: Identity = Depends(get_identity)):
    """Update the user (overwrite)"""
    provided_user = deserialize.user(identity.id, body)

    return serialize.user(UserService.save(provided_user))


@router.post("/self", response_model=User)
def post_self(body: UpdateUserRequest, identity: Identity = Depends(get_identity)):
    """Create the user (only if not exists)"""
    existing_user = UserService.by_identifier(identity.id)
    provided_user = deserialize.user(identity.id, body)

    save_user = provided_user if not existing_user else existing_user

    return serialize.user(UserService.save(save_user))
