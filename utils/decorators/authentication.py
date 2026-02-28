"""Authenticate requests via Google OAuth"""

from contextvars import ContextVar
from typing import Callable

import azure.functions as func

from utils.auth import Identity, verify_google_token
from utils.errors import AuthenticationError

_current_identity: ContextVar[Identity] = ContextVar("current_identity")


def get_identity() -> Identity:
    """Get the current request's identity from context"""
    return _current_identity.get()


def handle_authentication(
    function: Callable[[func.HttpRequest], func.HttpResponse],
) -> Callable[[func.HttpRequest], func.HttpResponse]:
    """Validate the Bearer token and stash the identity on the request"""

    def inner_function(req: func.HttpRequest):
        auth_header = req.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            raise AuthenticationError("Missing Bearer token")

        token = auth_header[len("Bearer ") :]

        try:
            identifier = verify_google_token(token)
        except ValueError as exc:
            raise AuthenticationError(str(exc)) from exc

        token = _current_identity.set(Identity(id=identifier))
        try:
            return function(req)
        finally:
            _current_identity.reset(token)

    return inner_function
