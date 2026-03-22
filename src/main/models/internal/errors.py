"""Application-level HTTP error types"""


class AuthenticationError(Exception):
    """Raised when a request cannot be authenticated (401)"""


class AuthorizationError(Exception):
    """Raised when a request is authenticated but not authorized (403)"""


class NotFoundError(Exception):
    """Raised when a request requests a resource that cannot be found (404)"""


class BadRequestError(Exception):
    """Raised when a request is incorrect (400)"""
