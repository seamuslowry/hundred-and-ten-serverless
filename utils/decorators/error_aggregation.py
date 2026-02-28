"""Transform errors into HTTP responses"""

from typing import Callable

import azure.functions as func

from utils.errors import AuthenticationError, AuthorizationError
from utils.models import HundredAndTenError


def handle_error(
    function: Callable[[func.HttpRequest], func.HttpResponse],
) -> Callable[[func.HttpRequest], func.HttpResponse]:
    """Aggregate error handlers into one decorator"""

    def inner_function(req: func.HttpRequest):
        try:
            return function(req)
        except AuthenticationError as exception:
            return func.HttpResponse(status_code=401, body=str(exception))
        except AuthorizationError as exception:
            return func.HttpResponse(status_code=403, body=str(exception))
        except (HundredAndTenError, ValueError) as exception:
            return func.HttpResponse(status_code=400, body=str(exception))

    return inner_function
