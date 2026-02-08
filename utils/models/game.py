"""Model a Hundred and Ten game through its lifecycle (lobby and play phases)."""

from dataclasses import InitVar, dataclass, field
from typing import Optional, Union, override
from uuid import uuid4

from hundredandten import HundredAndTen
from hundredandten.actions import Action
from hundredandten.constants import RoundStatus
from hundredandten.group import Group, Player
from hundredandten.round import Round

from utils.constants import Accessibility, GameRole, GameStatus
from utils.models.person import Person


class PersonGroup(list[Person]):
    """A group of persons in a game"""

    def find_or_throw(self, identifier: str) -> Person:
        """Find the person with the passed identifier; throw if they don't exist"""
        p = self._by_identifier(identifier)
        if not p:
            raise ValueError(f"Unable to find {identifier}")
        return p

    def find_or_append(self, identifier: str, backup: Person) -> Person:
        """Find the person with the passed identifier; return the backup if they don't exist"""
        p = self._by_identifier(identifier)
        if not p:
            self.append(backup)
            return backup
        return p

    def _by_identifier(self, identifier: str) -> Optional[Person]:
        """Find a person by identifier"""
        return next((p for p in self if p.identifier == identifier), None)

    def by_role(self, role: GameRole) -> list[Person]:
        """Find all persons with a specific role"""
        return [p for p in self if role in p.roles]


@dataclass
class BaseGame:
    """Shared fields and properties for Lobby and Game"""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = field(default="")
    seed: str = field(default_factory=lambda: str(uuid4()))
    accessibility: Accessibility = field(default=Accessibility.PUBLIC)
    people: PersonGroup = field(default_factory=PersonGroup)

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
    def invitees(self) -> list[Person]:
        """Get people who have been invited but not joined"""
        return self.people.by_role(GameRole.INVITEE)

    def automate(self, identifier: str) -> None:
        """Automate a player"""
        person = self.people.find_or_throw(identifier)
        person.automate = True


@dataclass
class Lobby(BaseGame):
    """A class to model the lobby phase of a Hundred and Ten game"""

    def join(self, identifier: str) -> None:
        """Add a player to the lobby"""
        person = self.people.find_or_append(identifier, Person(identifier=identifier))

        if self.accessibility == Accessibility.PRIVATE:
            if not (
                person
                and (
                    GameRole.INVITEE in person.roles or GameRole.PLAYER in person.roles
                )
            ):
                raise ValueError("Cannot join private game without invitation")

        person.roles.add(GameRole.PLAYER)

    def leave(self, identifier: str) -> None:
        """Remove a player from the lobby"""
        # for now, you can "leave" even if not in the game
        person = self.people.find_or_append(identifier, Person(identifier))
        self.people.remove(person)

    def invite(self, inviter: str, invitee: str) -> None:
        """Invite someone to the game"""
        inviter_person = self.people.find_or_throw(inviter)
        if (
            GameRole.PLAYER not in inviter_person.roles
            and GameRole.ORGANIZER not in inviter_person.roles
        ):
            raise ValueError("Only players or organizer can invite")

        self.people.find_or_append(invitee, Person(identifier=invitee)).roles.add(
            GameRole.INVITEE
        )


@dataclass
class Game(BaseGame):
    """A class to model an in-progress or completed Hundred and Ten game"""

    initial_moves: InitVar[Optional[list[Action]]] = None

    # The underlying game engine (always exists for a Game)
    _game: HundredAndTen = field(init=False, repr=False)

    def __post_init__(self, initial_moves: Optional[list[Action]]):
        self._game = self._initialize_game(initial_moves or [])

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
    def status(self) -> Union[GameStatus, RoundStatus]:
        """Get the current game status"""
        if self._game.winner:
            return GameStatus.WON
        return self._game.active_round.status

    @property
    def winner(self) -> Optional[Person]:
        """Get the winner of the game"""
        if self._game.winner:
            return self.people.find_or_throw(self._game.winner.identifier)
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
    def automate(self, identifier: str) -> None:
        """Automate a player (used when leaving an active game)"""
        super().automate(identifier)
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
