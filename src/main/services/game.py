"""Facilitate interaction with the game DB"""

from beanie.operators import Or, RegEx

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
        result = await DbGame.get(game_id)
        if not result:
            raise ValueError(f"No game found with id {game_id}")

        return deserialize.game(result)

    @staticmethod
    async def search(player_id: str, search_game: SearchGamesRequest) -> list[Game]:
        """Search for games matching the provided criteria"""

        # active_player = search_game.get("active_player", None)
        # winner = search_game.get("winner", None)
        # statuses = search_game.get("statuses", None)

        return list(
            map(
                deserialize.game,
                await DbGame.find(
                    RegEx(DbGame.name, search_game.searchText, "i"),
                    Or(
                        DbGame.accessibility == Accessibility.PUBLIC,
                        DbGame.players.identifier == player_id,
                        DbGame.organizer.identifier == player_id,
                    ),
                    DbGame.active_player == search_game.activePlayer,
                    DbGame.winner == search_game.winner,
                )
                .limit(search_game.limit)
                .skip(search_game.offset)
                .to_list(),
            )
        )

        # return list(
        #     map(
        #         deserialize.game,
        #         game_client.find(
        #             {
        #                 "type": "game",
        #                 "name": {"$regex": search_game["name"], "$options": "i"},
        #                 "$or": [
        #                     {"accessibility": Accessibility.PUBLIC.name},
        #                     {
        #                         "people": {
        #                             "$elemMatch": {
        #                                 "identifier": {"$eq": search_game["client"]}
        #                             }
        #                         }
        #                     },
        #                 ],
        #                 **(
        #                     {"active_player": active_player}
        #                     if active_player is not None
        #                     else {}
        #                 ),
        #                 **({"winner": winner} if winner is not None else {}),
        #                 **(
        #                     {"status": {"$in": statuses}}
        #                     if statuses is not None
        #                     else {}
        #                 ),
        #             }
        #         ).limit(max_count),
        #     )
        # )
