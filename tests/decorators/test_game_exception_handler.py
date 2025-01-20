'''Game exception handler unit tests'''
from unittest import TestCase

import azure.functions as func

from utils.decorators.error_aggregation import handle_error
from utils.models import HundredAndTenError
from tests.helpers import build_request


class TestGameExceptionHandler(TestCase):
    '''Game Excetpion handler unit tests'''

    def test_does_nothing_when_no_exception(self):
        '''Function returns as expected when no exception occurs'''
        status_code = 204
        wrapped_func = handle_error(lambda r: func.HttpResponse(status_code=status_code))

        self.assertEqual(status_code, wrapped_func(build_request()).status_code)

    def test_returns_bad_request_when_exception_is_caught(self):
        '''Function returns 400 when an exception occurs'''
        def test_func(req):
            raise HundredAndTenError('')

        wrapped_func = handle_error(test_func)

        self.assertEqual(400, wrapped_func(build_request()).status_code)
