"""Shared configuration for the client representation of a game of Hundred and Ten"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ClientModel(BaseModel):
    """Base model with camelCase alias generation for JSON serialization."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
    )
