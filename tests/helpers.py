'''Helpers to perform common functions during testing'''
import json
from typing import Optional

import azure.functions as func

from functions.create_game import create_game as wrapped_create_game
from functions.leave_game import leave_game as wrapped_leave_game
from functions.self import update_self as wrapped_self
from functions.start_game import start_game as wrapped_start_game
from functions.suggestion import suggestion as wrapped_suggestion
from utils import models
from utils.dtos.client import (CompletedGame, StartedGame, Suggestion, User,
                               WaitingGame)

create_game = wrapped_create_game.build().get_user_function()
leave_game = wrapped_leave_game.build().get_user_function()
self_http = wrapped_self.build().get_user_function()
start_game = wrapped_start_game.build().get_user_function()
suggestion = wrapped_suggestion.build().get_user_function()

DEFAULT_ID = 'id'
DEFAULT_NAME = 'name'


def build_request(method='GET', body=None, route_params=None,
                  headers: Optional[dict[str, str]] = None, params=None):
    '''Build a request defaulting common values for the arguments'''
    return func.HttpRequest(
        method=method, body=json.dumps(body).encode('utf-8') if body else b'',
        route_params=route_params, url='',
        headers={'x-ms-client-principal-idp': 'unknown', 'x-ms-client-principal-id': DEFAULT_ID,
                 'x-ms-client-principal-name': DEFAULT_NAME, **(headers or {})},
        params=params)


def read_response_body(body: bytes):
    '''Read the response body and return it as a dict'''
    return json.loads(body.decode('utf-8'))


def lobby_game(organizer: str = DEFAULT_ID, organizer_name: str = DEFAULT_NAME) -> WaitingGame:
    '''Get a started game waiting for the players'''
    resp = create_game(
        build_request(
            headers={'x-ms-client-principal-id': organizer,
                     'x-ms-client-principal-name': organizer_name},
            body={'name': 'test game'}))
    return read_response_body(resp.get_body())


def create_user(identifier: str, name: str = '') -> User:
    '''Attempt to create a user for the first time'''
    return __user('POST', models.User(
        identifier=identifier,
        name=name
    ))


def update_user(identifier: str, name: str = '') -> User:
    '''Update an existing user if possible'''
    return __user('PUT', models.User(
        identifier=identifier,
        name=name
    ))


def __user(method: str, user: models.User) -> User:
    '''Update an existing user if possible'''
    return read_response_body(self_http(
        build_request(
            method=method,
            body={'name': user.name, 'picture_url': user.picture_url},
            headers={'x-ms-client-principal-id': user.identifier})).get_body())


def started_game() -> StartedGame:
    '''Get a started game waiting for the first move'''
    created_game: WaitingGame = lobby_game()
    resp = start_game(
        build_request(
            route_params={'game_id': created_game['id']},
            headers={'x-ms-client-principal-id': created_game['organizer']['identifier']}))
    return read_response_body(resp.get_body())


def completed_game() -> CompletedGame:
    '''Get a completed game'''
    game = started_game()

    active_player = game['round']['active_player']
    assert active_player

    resp = leave_game(
        build_request(
            route_params={'game_id': game['id']},
            headers={'x-ms-client-principal-id': active_player['identifier']}))
    return read_response_body(resp.get_body())


def request_suggestion(game_id: str, user: str = DEFAULT_ID) -> func.HttpResponse:
    '''get the suggestion for the game'''
    return suggestion(
        build_request(
            route_params={'game_id': game_id},
            headers={'x-ms-client-principal-id': user}))


def get_suggestion(game_id: str) -> Suggestion:
    '''get the suggestion for the game'''
    resp = request_suggestion(game_id)
    return read_response_body(resp.get_body())
