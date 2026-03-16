"""Format of a players of Hundred and Ten in the DB"""

from abc import ABC
from typing import Annotated, Literal, Optional, Union

from beanie import Document
from pydantic import BaseModel, Field


class AbstractPlayerInGame(ABC, BaseModel):
    """A base class for players"""

    player_id: str


class HumanPlayer(AbstractPlayerInGame):
    """A human player"""

    type: Literal["human"] = "human"


class NaiveCpuPlayer(AbstractPlayerInGame):
    """A naive CPU player"""

    type: Literal["naive"] = "naive"


type PlayerInGame = Annotated[
    Union[HumanPlayer, NaiveCpuPlayer], Field(discriminator="type")
]


class Player(ABC, Document):
    """A base class for players"""

    class Settings:
        """Settings for the base player beanie model"""

        is_root = True
        name = "players"  # the collection
        class_id = "schema_version"  # the field to discriminate on

    player_id: str
    name: str
    picture_url: Optional[str]


class PlayerV0(Player):
    """A V0 player document"""
