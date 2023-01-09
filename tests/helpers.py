'''Helpers to perform common functions during testing'''
import json
from typing import Optional, Union

import azure.functions as func

from app.models import (Bid, BidAmount, DetailedDiscard, GameRole, GameStatus,
                        Group, Person, RoundStatus, SelectableSuit,
                        SelectTrump, Trick)
from app.models.game import Game

DEFAULT_ID = 'id'


def build_request(method='GET', body=None, route_params=None,
                  headers: Optional[dict[str, str]] = None, params=None):
    '''Build a request defaulting common values for the arguments'''
    return func.HttpRequest(
        method=method, body=json.dumps(body).encode('utf-8') if body else b'',
        route_params=route_params, url='',
        headers={'x-ms-client-principal-idp': 'unknown', 'x-ms-client-principal-id': DEFAULT_ID,
                 'x-ms-client-principal-name': 'name', **(headers or {})},
        params=params)


def read_response_body(body: bytes):
    '''Read the response body and return it as a dict'''
    return json.loads(body.decode('utf-8'))


def return_input(param):
    '''Return the parameter; useful for mocks'''
    return param


def game(
        status: Union[GameStatus, RoundStatus]) -> Game:
    '''
    Return a game in the requested status.
    '''

    new_game = {
        GameStatus.WAITING_FOR_PLAYERS: __get_waiting_for_players_game,
        RoundStatus.BIDDING: __get_bidding_game,
        RoundStatus.COMPLETED_NO_BIDDERS: __get_completed_no_bidders_game,
        RoundStatus.TRUMP_SELECTION: __get_trump_selection_game,
        RoundStatus.DISCARD: __get_discard_game,
        RoundStatus.TRICKS: __get_tricks_game
    }[status]()
    return new_game


def __get_waiting_for_players_game() -> Game:
    '''Returns a game that is waiting for players'''
    new_game = Game(
        people=Group(
            list(map(
                lambda identifier: Person(str(identifier), roles={GameRole.PLAYER}),
                ['0', DEFAULT_ID, *range(1, 3)]))))
    new_game.people.add_role(new_game.people[0].identifier, GameRole.ORGANIZER)
    return new_game


def __get_bidding_game() -> Game:
    '''Returns a game in the bidding status'''
    new_game = __get_waiting_for_players_game()
    new_game.start_game()
    return new_game


def __get_completed_no_bidders_game() -> Game:
    '''Returns a game in the completed no bidders status'''
    new_game = __get_bidding_game()
    new_game.active_round.bids = [Bid(p.identifier, BidAmount.PASS) for p in new_game.players]
    return new_game


def __get_trump_selection_game() -> Game:
    '''Return a game in the trump selection status'''
    new_game = __get_bidding_game()
    new_game.active_round.bids = [Bid(p.identifier, BidAmount.PASS)
                                  for p in new_game.active_round.inactive_players] + [
        Bid(new_game.active_round.active_player.identifier, BidAmount.FIFTEEN)]
    return new_game


def __get_discard_game() -> Game:
    '''Return a game in the discard status'''
    new_game = __get_trump_selection_game()
    active_bidder = new_game.active_round.active_bidder
    assert active_bidder
    new_game.active_round.selection = SelectTrump(
        active_bidder.identifier, SelectableSuit.DIAMONDS)
    return new_game


def __get_tricks_game() -> Game:
    '''Return a game in the tricks status'''
    new_game = __get_discard_game()
    new_game.active_round.discards = [DetailedDiscard(
        p.identifier, [], p.hand) for p in new_game.active_round.players]

    trump = new_game.active_round.trump
    assert trump
    new_game.active_round.tricks = [Trick(trump)]

    return new_game
