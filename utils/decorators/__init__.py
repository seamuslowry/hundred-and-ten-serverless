"""Init the decorators module"""

from utils.decorators.authentication import (
    get_identity,
)
from utils.decorators.authentication import (
    handle_authentication as authenticate,
)
from utils.decorators.error_aggregation import handle_error as catcher

__all__ = ["authenticate", "catcher", "get_identity"]
