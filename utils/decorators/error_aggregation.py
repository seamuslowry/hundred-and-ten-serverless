'''Transfrom errors into HTTP responses'''
from typing import Callable

import azure.functions as func

from utils.models import HundredAndTenError


def handle_error(function: Callable[[func.HttpRequest],
                                    func.HttpResponse]) -> Callable[[func.HttpRequest],
                                                                    func.HttpResponse]:
    '''Aggregate error handlers into one decorator'''
    def inner_function(req: func.HttpRequest):
        try:
            return function(req)
        except (HundredAndTenError, ValueError) as exception:
            return func.HttpResponse(status_code=400, body=str(exception))
    return inner_function
