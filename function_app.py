"""
The entrypoint for azure functions, wrapping a FastAPI app via AsgiFunctionApp
"""

import os
from contextlib import asynccontextmanager

import azure.functions as func
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from hundredandten.engine.errors import HundredAndTenError

from src.auth import (
    get_authorized_identity_for_path_player,
)
from src.models.db.setup import initialize_odm
from src.models.internal.errors import (
    AuthenticationError,
    AuthorizationError,
    BadRequestError,
    NotFoundError,
)
from src.routers import games, lobbies, players

# =============================================================================
# Context manager
# =============================================================================


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize the context of FastAPI"""
    await initialize_odm()
    yield


# =============================================================================
# FastAPI app
# =============================================================================


fastapi_app = FastAPI(
    dependencies=[Depends(get_authorized_identity_for_path_player)], lifespan=lifespan
)


# =============================================================================
# CORS middleware
# =============================================================================


fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        os.getenv("CORS_ORIGINS", "").split(",")
        if os.getenv("CORS_ORIGINS")
        else ["http://localhost:3000"]
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Exception handlers
# =============================================================================


@fastapi_app.exception_handler(AuthenticationError)
async def authentication_error_handler(
    _: Request, exc: AuthenticationError
) -> JSONResponse:
    """Return 401 for authentication errors"""
    return JSONResponse(status_code=401, content=str(exc))


@fastapi_app.exception_handler(NotFoundError)
async def not_found_error_handler(_: Request, exc: NotFoundError) -> JSONResponse:
    """Return 404 for not found errors"""
    return JSONResponse(status_code=404, content=str(exc))


@fastapi_app.exception_handler(BadRequestError)
async def bad_request_error_handler(_: Request, exc: NotFoundError) -> JSONResponse:
    """Return 404 for not found errors"""
    return JSONResponse(status_code=400, content=str(exc))


@fastapi_app.exception_handler(AuthorizationError)
async def authorization_error_handler(
    _: Request, exc: AuthorizationError
) -> JSONResponse:
    """Return 403 for authorization errors"""
    return JSONResponse(status_code=403, content=str(exc))


@fastapi_app.exception_handler(HundredAndTenError)
async def game_error_handler(_: Request, exc: HundredAndTenError) -> JSONResponse:
    """Return 400 for game errors"""
    return JSONResponse(status_code=400, content=str(exc))


@fastapi_app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    """Return 400 for value errors"""
    return JSONResponse(status_code=400, content=str(exc))


# =============================================================================
# Routers
# =============================================================================

fastapi_app.include_router(players)
fastapi_app.include_router(lobbies)
fastapi_app.include_router(games)

# =============================================================================
# Azure Functions ASGI wrapper
# =============================================================================

app = func.AsgiFunctionApp(app=fastapi_app, http_auth_level=func.AuthLevel.ANONYMOUS)
