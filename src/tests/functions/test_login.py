"""Retrieve login unit tests"""

from time import time

from fastapi.testclient import TestClient

from src.tests.helpers import create_user, update_user


class TestLogin:
    """Unit tests to create / update user as a client"""

    def test_post_user(self, client: TestClient):
        """Can post a new user"""
        identifier = f"{time()}"
        user = create_user(client, identifier)

        assert identifier == user["identifier"]

    def test_put_user(self, client: TestClient):
        """Can update an existing user"""
        identifier = f"{time()}"
        new_name = "new_name"
        original_user = create_user(client, identifier, "old_name")
        updated_user = update_user(client, identifier, new_name)

        assert original_user["identifier"] == updated_user["identifier"]
        assert original_user["name"] != updated_user["name"]
        assert new_name == updated_user["name"]

    def test_cannot_recreate_user(self, client: TestClient):
        """Cannot recreate a user"""
        identifier = f"{time()}"
        old_name = "old_name"
        original_user = create_user(client, identifier, "old_name")
        updated_user = create_user(client, identifier, "new_name")

        assert original_user["identifier"] == updated_user["identifier"]
        assert original_user["name"] == updated_user["name"]
        assert old_name == updated_user["name"]
