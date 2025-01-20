'''Model user-related information.'''


from dataclasses import dataclass, field
from typing import Optional


@dataclass
class User:
    '''A class to interact with generic users'''
    identifier: str
    name: str = field(compare=False)
    picture_url: Optional[str] = field(compare=False, default=None)
