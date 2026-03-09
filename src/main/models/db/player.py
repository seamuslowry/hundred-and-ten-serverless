"""Format of a players of Hundred and Ten in the DB"""

from abc import ABC
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class AbstractPlayer(ABC, BaseModel):
    """A base class for players"""

    identifier: str


class HumanPlayer(AbstractPlayer):
    """A human player"""

    type: Literal["human"] = "human"


class NaiveCpuPlayer(AbstractPlayer):
    """A naive CPU player"""

    type: Literal["naive"] = "naive"


type Player = Annotated[Union[HumanPlayer, NaiveCpuPlayer], Field(discriminator="type")]
