'''Model the game of Hundred and Ten that is being played.'''

from dataclasses import dataclass, field
from uuid import uuid4

from hundredandten import HundredAndTen


@dataclass
class Game(HundredAndTen):
    '''A class to model the Hundred and Ten game'''
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = field(default='')
