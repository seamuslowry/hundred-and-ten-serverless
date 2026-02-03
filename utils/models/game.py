"""Model the game of Hundred and Ten that is being played."""

from dataclasses import InitVar, dataclass, field
from typing import Optional, Union
from uuid import uuid4

from hundredandten import HundredAndTen
from hundredandten.actions import Action
from hundredandten.constants import RoundStatus
from hundredandten.group import Group, Player
from hundredandten.round import Round

from utils.constants import Accessibility, GameRole, GameStatus
from utils.models.lobby import Lobby, PersonGroup
from utils.models.person import Person


@dataclass
class Game:
    """A class to model an in-progress or completed Hundred and Ten game"""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = field(default="")
    seed: str = field(default_factory=lambda: str(uuid4()))
    accessibility: Accessibility = field(default=Accessibility.PUBLIC)
    people: PersonGroup = field(default_factory=PersonGroup)

    initial_moves: InitVar[list[Action]] = field(default_factory=list)

    # The underlying game engine (always exists for a Game)
    _game: HundredAndTen = field(init=False, repr=False)

    def __post_init__(self, initial_moves: list[Action]):
        self._game = self._initialize_game(initial_moves)

    @classmethod
    def from_lobby(cls, lobby: Lobby) -> "Game":
        """Create a Game from a Lobby (starts the game)"""
        if len(lobby.players) < 2:
            raise ValueError("Need at least 2 players to start")

        return cls(
            id=lobby.id,
            name=lobby.name,
            seed=lobby.seed,
            accessibility=lobby.accessibility,
            people=lobby.people,
            initial_moves=[],
        )

    @property
    def moves(self) -> list[Action]:
        """Get all moves made in the game"""
        return self._game.moves

    @property
    def organizer(self) -> Person:
        """Get the organizer of the game"""
        organizers = self.people.by_role(GameRole.ORGANIZER)
        if organizers:
            return organizers[0]
        if self.people:
            return self.people[0]
        return Person(identifier="unknown")

    @property
    def players(self) -> list[Person]:
        """Get players who have joined the game"""
        return self.people.by_role(GameRole.PLAYER)

    @property
    def status(self) -> Union[GameStatus, RoundStatus]:
        """Get the current game status"""
        if self._game.winner:
            return GameStatus.WON
        return self._game.active_round.status

    @property
    def winner(self) -> Optional[Person]:
        """Get the winner of the game"""
        if self._game.winner:
            return self.people.by_identifier(self._game.winner.identifier)
        return None

    @property
    def active_round(self) -> Round:
        """Get the current active round"""
        return self._game.active_round

    @property
    def events(self) -> list:
        """Get all game events"""
        return self._game.events

    @property
    def scores(self) -> dict[str, int]:
        """Get current scores"""
        return self._game.scores

    def automate(self, identifier: str) -> None:
        """Automate a player (used when leaving an active game)"""
        person = self.people.by_identifier(identifier)
        if person:
            person.automate = True
        self._game = self._initialize_game(self.moves)

    def act(self, action: Action) -> None:
        """Perform a game action"""
        self._game.act(action)

    def suggestion(self) -> Action:
        """Get a suggested action"""
        return self._game.suggestion()

    def _initialize_game(self, moves: list[Action]) -> HundredAndTen:
        return HundredAndTen(
            players=Group(
                [
                    Player(identifier=p.identifier, automate=p.automate)
                    for p in self.players
                ]
            ),
            seed=self.seed,
            initial_moves=moves,
        )
