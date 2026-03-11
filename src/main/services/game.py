"""Facilitate interaction with the game DB"""

from beanie.operators import ElemMatch, In, Or, RegEx

from src.main.mappers.db import deserialize, serialize
from src.main.models.client.requests import SearchGamesRequest
from src.main.models.db import Game as DbGame
from src.main.models.db.lobby import Accessibility
from src.main.models.internal import Game


class GameService:
    """A service used to handle the business logic of games"""

    @staticmethod
    async def save(game: Game) -> Game:
        """Save the provided game to the DB"""
        return deserialize.game(await serialize.game(game).save())

    @staticmethod
    async def get(game_id: str) -> Game:
        """Retrieve the game with the provided ID"""
        result = await DbGame.get(game_id, with_children=True)
        if not result:
            raise ValueError(f"No game found with id {game_id}")

        return deserialize.game(result)

    @staticmethod
    async def search(player_id: str, search_game: SearchGamesRequest) -> list[Game]:
        """Search for games matching the provided criteria"""

        filters = [
            RegEx(DbGame.name, search_game.search_text, "i"),
            Or(
                DbGame.accessibility == Accessibility.PUBLIC,
                ElemMatch(DbGame.players, {"identifier": player_id}),
                DbGame.organizer.identifier == player_id,
            ),
        ]
        if search_game.active_player is not None:
            filters.append(DbGame.active_player == search_game.active_player)
        if search_game.winner is not None:
            filters.append(DbGame.winner == search_game.winner)
        if search_game.statuses is not None:
            filters.append(In(DbGame.status, search_game.statuses))

        return list(
            map(
                deserialize.game,
                await DbGame.find(*filters, with_children=True)
                .limit(search_game.limit)
                .skip(search_game.offset)
                .to_list(),
            )
        )
