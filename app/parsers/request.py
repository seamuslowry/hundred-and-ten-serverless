'''
Parse models off an HTTP request
'''
from typing import Tuple

import azure.functions as func

from app.mappers.client import deserialize
from app.models import Game, User
from app.services import GameService, UserService


def parse(req: func.HttpRequest) -> Tuple[User, Game]:
    '''
    Parse the request for the models
    '''
    game_id = req.route_params.get('game_id', None)
    # TODO let exception be thrown; catch
    game = GameService.get(game_id) if game_id else Game()

    return (UserService.save(deserialize.user(req)), game)
