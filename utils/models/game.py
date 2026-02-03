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
from utils.models.person import Person


class PersonGroup(list[Person]):
    """A group of persons in the lobby phase"""

    def by_identifier(self, identifier: str) -> Optional[Person]:
        """Find a person by identifier"""
        return next((p for p in self if p.identifier == identifier), None)

    def by_role(self, role: GameRole) -> list[Person]:
        """Find all persons with a specific role"""
        return [p for p in self if role in p.roles]


@dataclass
class Game:
    """A class to model the Hundred and Ten game with lobby support"""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = field(default="")
    seed: str = field(default_factory=lambda: str(uuid4()))
    accessibility: Accessibility = field(default=Accessibility.PUBLIC)
    lobby: bool = field(default=True)
    # don't want to have to keep this in sync with game players.
    # should refactor into a separate Lobby model
    people: PersonGroup = field(default_factory=PersonGroup)

    initial_moves: InitVar[Optional[list[Action]]] = field(default=None)

    # The underlying game engine
    _game: Optional[HundredAndTen] = field(default=None, init=False, repr=False)

    def __post_init__(self, initial_moves: Optional[list[Action]]):
        if not self.lobby:
            self._game = self._initialize_game(initial_moves or [])

    @property
    def moves(self) -> list[Action]:
        """Get all moves made in the game"""
        return self._game.moves if self._game else []

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

    @property
    def status(self) -> Union[GameStatus, RoundStatus]:
        """Get the current game status"""
        if self.lobby or not self._game:
            return GameStatus.WAITING_FOR_PLAYERS
        if self._game.winner:
            return GameStatus.WON
        return self._game.active_round.status

    @property
    def winner(self) -> Optional[Person]:
        """Get the winner of the game"""
        if self._game and self._game.winner:
            return self.people.by_identifier(self._game.winner.identifier)
        return None

    @property
    def active_round(self) -> Round:
        """Get the current active round"""
        if not self._game:
            raise ValueError("Game has not started")
        return self._game.active_round

    @property
    def events(self) -> list:
        """Get all game events"""
        if self._game:
            return self._game.events
        return []

    @property
    def scores(self) -> dict[str, int]:
        """Get current scores"""
        if self._game:
            return self._game.scores
        return {}

    def join(self, identifier: str) -> None:
        """Add a player to the game"""
        if self.status != GameStatus.WAITING_FOR_PLAYERS:
            raise ValueError("Cannot join an in-progress game")

        person = self.people.by_identifier(identifier)

        if self.accessibility == Accessibility.PRIVATE:
            # Check if invited or already a player
            if not (
                person
                and (
                    GameRole.INVITEE in person.roles or GameRole.PLAYER in person.roles
                )
            ):
                raise ValueError("Cannot join private game without invitation")

        if person:
            person.roles.add(GameRole.PLAYER)
        else:
            self.people.append(Person(identifier=identifier, roles={GameRole.PLAYER}))

    def leave(self, identifier: str) -> None:
        """Remove a player from the game"""
        if not self.lobby:
            # For active games, automate instead
            self.automate(identifier)
            return
        person = self.people.by_identifier(identifier)
        if person:
            self.people.remove(person)

    def invite(self, inviter: str, invitee: str) -> None:
        """Invite someone to the game"""
        if not self.lobby:
            raise ValueError("Cannot invite to a game that has started")
        # Check inviter has permission
        inviter_person = self.people.by_identifier(inviter)
        if not inviter_person:
            raise ValueError("Inviter not in game")
        if (
            GameRole.PLAYER not in inviter_person.roles
            and GameRole.ORGANIZER not in inviter_person.roles
        ):
            raise ValueError("Only players or organizer can invite")

        existing = self.people.by_identifier(invitee)
        if not existing:
            self.people.append(Person(identifier=invitee, roles={GameRole.INVITEE}))

    def automate(self, identifier: str) -> None:
        """Automate a player"""
        person = self.people.by_identifier(identifier)
        if person:
            person.automate = True
        if self._game:
            self._game = self._initialize_game(self.moves)

    def start_game(self) -> None:
        """Start the game with current players"""
        if self._game or not self.lobby:
            raise ValueError("Game already started")
        if len(self.players) < 2:
            raise ValueError("Need at least 2 players to start")

        # Not a lobby anymore
        self.lobby = False

        # Create the game
        self._game = self._initialize_game([])

    def act(self, action: Action) -> None:
        """Perform a game action"""
        if not self._game:
            raise ValueError("Game has not started")
        self._game.act(action)

    def suggestion(self) -> Action:
        """Get a suggested action"""
        if not self._game:
            raise ValueError("Game has not started")
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
