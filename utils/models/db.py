from pydantic import BaseModel, Field
from bson import ObjectId

# Custom Pydantic ObjectId field to handle serialization
class ObjectIdField(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    @classmethod
    def validate(cls, v):
        if not isinstance(v, (str, ObjectId)):
            raise TypeError('ObjectId must be a string or an ObjectId instance')
        return str(v)
    @classmethod
    def __modify_schema__(cls, schema):
        schema.update(type='string')


# Base Pydantic class with common configuration
class BaseModelWithConfig(BaseModel):
    class Config:
        json_encoders = {
            ObjectId: str,
        }
        arbitrary_types_allowed = True


class Person(BaseModelWithConfig):
    id: ObjectIdField
    name: str
    email: str


class Card(BaseModelWithConfig):
    id: ObjectIdField
    suit: str
    rank: str


class BidMove(BaseModelWithConfig):
    type: str = Field(discriminator='type')
    amount: int


class SelectTrumpMove(BaseModelWithConfig):
    type: str = Field(discriminator='type')
    suit: str


class DiscardMove(BaseModelWithConfig):
    type: str = Field(discriminator='type')
    card_id: ObjectIdField


class PlayMove(BaseModelWithConfig):
    type: str = Field(discriminator='type')
    card_id: ObjectIdField


# Move discriminated union using Pydantic Field
Move = Field(..., discriminator='type')


class Lobby(BaseModelWithConfig):
    id: ObjectIdField
    players: list[Person]
    game_id: ObjectIdField


class Game(BaseModelWithConfig):
    id: ObjectIdField
    state: str
    current_turn: int


class User(BaseModelWithConfig):
    id: ObjectIdField
    username: str
    email: str


class SearchLobby(BaseModelWithConfig):
    id: ObjectIdField


class SearchGame(BaseModelWithConfig):
    id: ObjectIdField
