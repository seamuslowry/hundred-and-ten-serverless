"""Tests for Pydantic DB models in utils/models/db.py"""

from unittest import TestCase

from bson import ObjectId
from pydantic import ValidationError

from utils.models.db import (
    BidMove,
    Card,
    DiscardMove,
    Game,
    Lobby,
    Move,
    Person,
    PlayMove,
    SearchGame,
    SearchLobby,
    SelectTrumpMove,
    User,
)


class TestPersonModel(TestCase):
    """Tests for the Person Pydantic model"""

    def test_valid_person(self):
        """Person model accepts valid data"""
        person = Person(identifier="player1", automate=False)
        self.assertEqual(person.identifier, "player1")
        self.assertFalse(person.automate)

    def test_person_model_dump(self):
        """Person model_dump returns correct dict"""
        person = Person(identifier="player1", automate=True)
        data = person.model_dump()
        self.assertEqual(data, {"identifier": "player1", "automate": True})


class TestCardModel(TestCase):
    """Tests for the Card Pydantic model"""

    def test_valid_card(self):
        """Card model accepts valid data"""
        card = Card(suit="HEARTS", number="ACE")
        self.assertEqual(card.suit, "HEARTS")
        self.assertEqual(card.number, "ACE")

    def test_card_model_dump(self):
        """Card model_dump returns correct dict"""
        card = Card(suit="SPADES", number="KING")
        data = card.model_dump()
        self.assertEqual(data, {"suit": "SPADES", "number": "KING"})


class TestMoveDiscriminatedUnion(TestCase):
    """Tests for discriminated union Move types"""

    def test_bid_move_discriminator(self):
        """BidMove has correct type discriminator"""
        move = BidMove(identifier="player1", amount=30)
        self.assertEqual(move.type, "bid")
        self.assertEqual(move.identifier, "player1")
        self.assertEqual(move.amount, 30)

    def test_select_trump_move_discriminator(self):
        """SelectTrumpMove has correct type discriminator"""
        move = SelectTrumpMove(identifier="player1", suit="HEARTS")
        self.assertEqual(move.type, "select_trump")

    def test_discard_move_discriminator(self):
        """DiscardMove has correct type discriminator"""
        move = DiscardMove(
            identifier="player1", cards=[Card(suit="HEARTS", number="ACE")]
        )
        self.assertEqual(move.type, "discard")
        self.assertEqual(len(move.cards), 1)

    def test_play_move_discriminator(self):
        """PlayMove has correct type discriminator"""
        move = PlayMove(
            identifier="player1", card=Card(suit="HEARTS", number="ACE")
        )
        self.assertEqual(move.type, "play")

    def test_move_union_bid_from_dict(self):
        """Move union correctly parses a bid move dict via discriminator"""
        from pydantic import TypeAdapter

        adapter = TypeAdapter(Move)
        move = adapter.validate_python(
            {"type": "bid", "identifier": "player1", "amount": 30}
        )
        self.assertIsInstance(move, BidMove)
        self.assertEqual(move.amount, 30)

    def test_move_union_select_trump_from_dict(self):
        """Move union correctly parses a select_trump move dict via discriminator"""
        from pydantic import TypeAdapter

        adapter = TypeAdapter(Move)
        move = adapter.validate_python(
            {"type": "select_trump", "identifier": "player1", "suit": "HEARTS"}
        )
        self.assertIsInstance(move, SelectTrumpMove)

    def test_move_union_discard_from_dict(self):
        """Move union correctly parses a discard move dict via discriminator"""
        from pydantic import TypeAdapter

        adapter = TypeAdapter(Move)
        move = adapter.validate_python(
            {
                "type": "discard",
                "identifier": "player1",
                "cards": [{"suit": "HEARTS", "number": "ACE"}],
            }
        )
        self.assertIsInstance(move, DiscardMove)

    def test_move_union_play_from_dict(self):
        """Move union correctly parses a play move dict via discriminator"""
        from pydantic import TypeAdapter

        adapter = TypeAdapter(Move)
        move = adapter.validate_python(
            {
                "type": "play",
                "identifier": "player1",
                "card": {"suit": "HEARTS", "number": "ACE"},
            }
        )
        self.assertIsInstance(move, PlayMove)

    def test_invalid_move_type_raises_validation_error(self):
        """Move union raises ValidationError for unknown discriminator values"""
        from pydantic import TypeAdapter

        adapter = TypeAdapter(Move)
        self.assertRaises(
            ValidationError,
            adapter.validate_python,
            {"type": "unknown", "identifier": "player1"},
        )


class TestLobbyModel(TestCase):
    """Tests for the Lobby Pydantic model"""

    def _make_lobby(self, **kwargs) -> dict:
        return {
            "name": "Test Lobby",
            "seed": "abc123",
            "accessibility": "PUBLIC",
            "organizer": {"identifier": "player1", "automate": False},
            "players": [],
            "invitees": [],
            **kwargs,
        }

    def test_lobby_without_id(self):
        """Lobby model can be created without _id"""
        lobby = Lobby.model_validate(self._make_lobby())
        self.assertIsNone(lobby.id)
        self.assertEqual(lobby.type, "lobby")

    def test_invalid_objectid_type_raises(self):
        """_parse_objectid raises ValueError for invalid types"""
        from utils.models.db import _parse_objectid

        self.assertRaises(ValueError, _parse_objectid, 12345)

    def test_lobby_with_objectid(self):
        """Lobby model converts ObjectId to string"""
        oid = ObjectId()
        lobby = Lobby.model_validate(self._make_lobby(**{"_id": oid}))
        self.assertEqual(lobby.id, str(oid))

    def test_lobby_with_string_id(self):
        """Lobby model accepts string id via Python field name"""
        lobby = Lobby(id="test_id", **self._make_lobby())
        self.assertEqual(lobby.id, "test_id")

    def test_lobby_model_dump_no_id(self):
        """Lobby model_dump with by_alias excludes None _id when exclude_none=True"""
        lobby = Lobby.model_validate(self._make_lobby())
        data = lobby.model_dump(by_alias=True, exclude_none=True)
        self.assertNotIn("_id", data)

    def test_lobby_model_dump_with_id(self):
        """Lobby model_dump includes _id when set"""
        lobby = Lobby(id="507f1f77bcf86cd799439011", **self._make_lobby())
        data = lobby.model_dump(by_alias=True)
        self.assertEqual(data["_id"], "507f1f77bcf86cd799439011")

    def test_lobby_type_default(self):
        """Lobby type defaults to 'lobby'"""
        lobby = Lobby.model_validate(self._make_lobby())
        self.assertEqual(lobby.type, "lobby")

    def test_lobby_populate_by_name(self):
        """Lobby accepts both '_id' alias and 'id' Python field name"""
        oid = ObjectId()
        # Via alias
        lobby1 = Lobby.model_validate({"_id": oid, **self._make_lobby()})
        # Via Python name
        lobby2 = Lobby(id=str(oid), **self._make_lobby())
        self.assertEqual(lobby1.id, lobby2.id)


class TestGameModel(TestCase):
    """Tests for the Game Pydantic model"""

    def _make_game(self, **kwargs) -> dict:
        return {
            "name": "Test Game",
            "seed": "abc123",
            "accessibility": "PUBLIC",
            "organizer": {"identifier": "player1", "automate": False},
            "players": [],
            "moves": [],
            "status": "PLAYING",
            **kwargs,
        }

    def test_game_with_objectid(self):
        """Game model converts ObjectId _id to string"""
        oid = ObjectId()
        game = Game.model_validate({"_id": oid, **self._make_game()})
        self.assertEqual(game.id, str(oid))

    def test_game_with_valid_moves(self):
        """Game model parses moves with discriminated union"""
        game = Game.model_validate(
            self._make_game(
                moves=[{"type": "bid", "identifier": "player1", "amount": 30}]
            )
        )
        self.assertEqual(len(game.moves), 1)
        self.assertIsInstance(game.moves[0], BidMove)

    def test_game_invalid_move_raises(self):
        """Game model raises ValidationError for invalid move type"""
        self.assertRaises(
            ValidationError,
            Game.model_validate,
            self._make_game(
                moves=[{"type": "unknown", "identifier": "player1"}]
            ),
        )

    def test_game_type_default(self):
        """Game type defaults to 'game'"""
        game = Game.model_validate(self._make_game())
        self.assertEqual(game.type, "game")

    def test_game_optional_fields_default_none(self):
        """Game optional fields default to None"""
        game = Game.model_validate(self._make_game())
        self.assertIsNone(game.winner)
        self.assertIsNone(game.active_player)
        self.assertIsNone(game.id)

    def test_game_model_dump_excludes_id(self):
        """Game model_dump with exclude={'id'} omits the _id field"""
        oid = ObjectId()
        game = Game.model_validate({"_id": oid, **self._make_game()})
        data = game.model_dump(by_alias=True, exclude={"id"})
        self.assertNotIn("_id", data)


class TestUserModel(TestCase):
    """Tests for the User Pydantic model"""

    def test_valid_user(self):
        """User model accepts valid data"""
        user = User(identifier="user1", name="Test User")
        self.assertEqual(user.identifier, "user1")
        self.assertEqual(user.name, "Test User")
        self.assertIsNone(user.picture_url)

    def test_user_with_picture_url(self):
        """User model accepts optional picture_url"""
        user = User(identifier="user1", name="Test User", picture_url="https://example.com/pic.jpg")
        self.assertEqual(user.picture_url, "https://example.com/pic.jpg")

    def test_user_model_dump(self):
        """User model_dump returns correct dict"""
        user = User(identifier="user1", name="Test User")
        data = user.model_dump(exclude_none=True)
        self.assertEqual(data, {"identifier": "user1", "name": "Test User"})


class TestSearchModels(TestCase):
    """Tests for SearchLobby and SearchGame Pydantic models"""

    def test_search_lobby(self):
        """SearchLobby model accepts valid data"""
        search = SearchLobby(name="test", client="player1")
        self.assertEqual(search.name, "test")
        self.assertEqual(search.client, "player1")

    def test_search_game_defaults(self):
        """SearchGame model has correct defaults"""
        search = SearchGame(name="test", client="player1")
        self.assertIsNone(search.statuses)
        self.assertIsNone(search.active_player)
        self.assertIsNone(search.winner)

    def test_search_game_with_all_fields(self):
        """SearchGame model accepts all optional fields"""
        search = SearchGame(
            name="test",
            client="player1",
            statuses=["PLAYING"],
            active_player="player1",
            winner="player2",
        )
        self.assertEqual(search.statuses, ["PLAYING"])
        self.assertEqual(search.active_player, "player1")
        self.assertEqual(search.winner, "player2")


class TestRoundTripSerialization(TestCase):
    """Tests for serialization/deserialization round trips"""

    def test_lobby_round_trip(self):
        """Lobby can be serialized and deserialized without loss"""
        oid = ObjectId()
        original = Lobby.model_validate(
            {
                "_id": oid,
                "name": "Round Trip Lobby",
                "seed": "test-seed",
                "accessibility": "PUBLIC",
                "organizer": {"identifier": "player1", "automate": False},
                "players": [{"identifier": "player2", "automate": False}],
                "invitees": [],
            }
        )
        data = original.model_dump(by_alias=True)
        restored = Lobby.model_validate(data)
        self.assertEqual(original.id, restored.id)
        self.assertEqual(original.name, restored.name)
        self.assertEqual(original.players[0].identifier, restored.players[0].identifier)

    def test_game_with_all_move_types_round_trip(self):
        """Game with all move types can be serialized and deserialized"""
        game = Game.model_validate(
            {
                "name": "Round Trip Game",
                "seed": "test-seed",
                "accessibility": "PUBLIC",
                "organizer": {"identifier": "player1", "automate": False},
                "players": [],
                "moves": [
                    {"type": "bid", "identifier": "player1", "amount": 30},
                    {"type": "select_trump", "identifier": "player1", "suit": "HEARTS"},
                    {
                        "type": "discard",
                        "identifier": "player1",
                        "cards": [{"suit": "HEARTS", "number": "ACE"}],
                    },
                    {
                        "type": "play",
                        "identifier": "player1",
                        "card": {"suit": "HEARTS", "number": "KING"},
                    },
                ],
                "status": "PLAYING",
            }
        )
        data = game.model_dump()
        restored = Game.model_validate(data)
        self.assertEqual(len(restored.moves), 4)
        self.assertIsInstance(restored.moves[0], BidMove)
        self.assertIsInstance(restored.moves[1], SelectTrumpMove)
        self.assertIsInstance(restored.moves[2], DiscardMove)
        self.assertIsInstance(restored.moves[3], PlayMove)

    def test_objectid_handling_in_round_trip(self):
        """BSON ObjectId is correctly handled in serialization round trip"""
        oid = ObjectId()
        game = Game.model_validate(
            {
                "_id": oid,
                "name": "test",
                "seed": "test",
                "accessibility": "PUBLIC",
                "organizer": {"identifier": "p1", "automate": False},
                "players": [],
                "moves": [],
                "status": "PLAYING",
            }
        )
        # ObjectId should be converted to string
        self.assertIsInstance(game.id, str)
        self.assertEqual(game.id, str(oid))

        # model_dump should produce a serializable dict
        data = game.model_dump(by_alias=True)
        self.assertIsInstance(data["_id"], str)
