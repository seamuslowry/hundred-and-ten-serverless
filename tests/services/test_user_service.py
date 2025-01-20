'''User Service unit tests'''
from time import time
from unittest import TestCase

from utils.models import User
from utils.services import UserService


class TestUserService(TestCase):
    '''Unit tests to ensure user operations work as expected'''

    def test_save_unknown_user(self):
        '''User can be saved to the DB'''
        user = User(identifier=str(time()), name='save_unknown')

        self.assertIsNotNone(UserService.save(user))

    def test_search_user(self):
        '''Users can be searched in the DB'''
        text = f'search_user{time()}'
        users = [UserService.save(
            User(identifier=str(time()), name=f'{text} {i}')) for i in range(5)]

        found_users = UserService.search(text)

        self.assertEqual(users, found_users)

    def test_get_users_by_identifiers(self):
        '''Users can be retrieved by identifier in the DB'''
        users = [UserService.save(
            User(identifier=str(time()), name='search')) for _ in range(5)]

        found_users = UserService.by_identifiers(list(map(lambda u: u.identifier, users)))

        self.assertEqual(users, found_users)
