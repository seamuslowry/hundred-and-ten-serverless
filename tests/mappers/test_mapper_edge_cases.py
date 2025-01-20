'''Ensure edge cases of mapping are unit tested'''
from unittest import TestCase

import azure.functions as func

from utils.mappers.client import deserialize, serialize
from utils.models import Action


class TestMapperEdgeCases(TestCase):
    '''Unit tests to ensure mapper edge cases behave as expected'''

    def test_bad_suggestion_error(self):
        '''Attempting to serialize an invalid suggestion results in an error'''
        identifier = 'identifier'
        self.assertRaises(ValueError, serialize.suggestion, Action(identifier), identifier)

    def test_incomplete_user_info(self):
        '''Attempting to serialize a user with incomplete header info results in an error'''
        self.assertRaises(ValueError, deserialize.user_id, func.HttpRequest(
            method='GET',
            body=b'',
            url='',
            headers={
            }
        ))
