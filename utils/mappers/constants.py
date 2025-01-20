'''Constants to support DB mapping'''
from enum import Enum


class EventType(str, Enum):
    '''Enum value for event types to client'''
    GAME_START = 1
    ROUND_START = 2
    BID = 3
    SELECT_TRUMP = 4
    DISCARD = 5
    TRICK_START = 6
    PLAY = 7
    TRICK_END = 8
    ROUND_END = 9
    GAME_END = 10
