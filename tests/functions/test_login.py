"""Retrieve login unit tests"""

from time import time
from unittest import TestCase

from tests.helpers import create_user, update_user


class TestLogin(TestCase):
    """Unit tests to create / update user as a client"""

    def test_post_user(self):
        """Can post a new user"""
        identifier = f"{time()}"
        user = create_user(identifier)

        self.assertEqual(identifier, user["identifier"])

    def test_put_user(self):
        """Can update an existing user"""
        identifier = f"{time()}"
        new_name = "new_name"
        original_user = create_user(identifier, "old_name")
        updated_user = update_user(identifier, new_name)

        self.assertEqual(original_user["identifier"], updated_user["identifier"])
        self.assertNotEqual(original_user["name"], updated_user["name"])
        self.assertEqual(new_name, updated_user["name"])

    def test_cannot_recreate_user(self):
        """Cannot recreate a user"""
        identifier = f"{time()}"
        old_name = "old_name"
        original_user = create_user(identifier, "old_name")
        updated_user = create_user(identifier, "new_name")

        self.assertEqual(original_user["identifier"], updated_user["identifier"])
        self.assertEqual(original_user["name"], updated_user["name"])
        self.assertEqual(old_name, updated_user["name"])
