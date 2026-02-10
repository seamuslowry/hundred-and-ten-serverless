"""Model a Hundred and Ten game through its lifecycle (lobby and play phases)."""

from abc import ABC, abstractmethod
from dataclasses import InitVar, dataclass, field
from typing import Optional, Union, override
from uuid import uuid4

from hundredandten import HundredAndTen
from hundredandten.actions import Action
from hundredandten.constants import RoundStatus
from hundredandten.group import Group, Player
from hundredandten.round import Round

from utils.constants import Accessibility, GameStatus
from utils.models.person import Person


class PersonGroup(list[Person]):
    """A group of persons in a game"""

    def find_or_throw(self, identifier: str) -> Person:
        """Find the person with the passed identifier; throw if they don't exist"""
        p = self._by_identifier(identifier)
        if not p:
            raise ValueError(f"Unable to find {identifier}")
        return p

    def find(self, identifier: str) -> Optional[Person]:
        """Find the person with the passed identifier; return None if they don't exist"""
        return self._by_identifier(identifier)

    def _by_identifier(self, identifier: str) -> Optional[Person]:
        """Find a person by identifier"""
        return next((p for p in self if p.identifier == identifier), None)


@dataclass
class BaseGame(ABC):
    """Shared fields and properties for Lobby and Game"""

    organizer: Person = field()
    players: PersonGroup = field(default_factory=PersonGroup)
    id: Optional[str] = field(default=None)
    name: str = field(default="")
    seed: str = field(default_factory=lambda: str(uuid4()))
    accessibility: Accessibility = field(default=Accessibility.PUBLIC)

    @abstractmethod
    def leave(self, identifier: str):
        """Leave the game or the lobby"""

    @property
    def ordered_players(self) -> PersonGroup:
        """The canonical order of all players in this game"""
        return PersonGroup([self.organizer, *self.players])


@dataclass
class Lobby(BaseGame):
    """A class to model the lobby phase of a Hundred and Ten game"""

    invitees: PersonGroup = field(default_factory=PersonGroup)

    def join(self, person: Person) -> None:
        """Add a player to the lobby"""
        if self.accessibility == Accessibility.PRIVATE and not self.invitees.find(
            person.identifier
        ):
            raise ValueError("Cannot join private game without invitation")

        self.players.append(person)

    def leave(self, identifier: str) -> None:
        """Remove a player from the lobby"""
        if identifier == self.organizer.identifier:
            raise ValueError("Organizer cannot leave a lobby")

        self.players.remove(self.players.find_or_throw(identifier))

    def invite(self, inviter: str, invitee: Person) -> None:
        """Invite someone to the game"""
        if self.organizer.identifier != inviter and self.players.find(inviter) is None:
            raise ValueError("Only players or organizer can invite")

        self.invitees.append(invitee)


@dataclass
class Game(BaseGame):
    """A class to model an in-progress or completed Hundred and Ten game"""

    initial_moves: InitVar[Optional[list[Action]]] = None

    # The underlying game engine (always exists for a Game)
    _game: HundredAndTen = field(init=False, repr=False)

    def __post_init__(self, initial_moves: Optional[list[Action]]):
        self._game = self._initialize_game(initial_moves or [])

    @staticmethod
    def from_lobby(lobby: Lobby) -> "Game":
        """Create a Game from a Lobby (starts the game)"""
        if len(lobby.ordered_players) < 2:
            raise ValueError("Need at least 2 players to start")

        return Game(
            id=lobby.id,
            name=lobby.name,
            seed=lobby.seed,
            accessibility=lobby.accessibility,
            organizer=lobby.organizer,
            players=lobby.players,
            initial_moves=[],
        )

    @property
    def moves(self) -> list[Action]:
        """Get all moves made in the game"""
        return self._game.moves

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
            return self.ordered_players.find_or_throw(self._game.winner.identifier)
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

    @override
    def leave(self, identifier: str) -> None:
        """Automate a player (used when leaving an active game)"""

        self.ordered_players.find_or_throw(identifier).automate = True
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
                    for p in self.ordered_players
                ]
            ),
            seed=self.seed,
            initial_moves=moves,
        )
