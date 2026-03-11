"""Format of a games of Hundred and Ten in the DB"""

from abc import ABC
from typing import Optional

from beanie import Document


class User(ABC, Document):
    """A base class for users"""

    class Settings:
        """Settings for the base user beanie model"""

        is_root = True
        name = "users"  # the collection
        class_id = "schema_version"  # the field to discriminate on

    identifier: str
    name: str
    picture_url: Optional[str]


class UserV0(User):
    """A V0 user document"""
