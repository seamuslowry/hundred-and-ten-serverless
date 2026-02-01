"""Model the game of Hundred and Ten that is being played."""

from dataclasses import dataclass, field
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

    def add_role(self, identifier: str, role: GameRole) -> None:
        """Add a role to a person"""
        person = self.by_identifier(identifier)
        if person:
            person.roles.add(role)

    def remove_role(self, identifier: str, role: GameRole) -> None:
        """Remove a role from a person"""
        person = self.by_identifier(identifier)
        if person:
            person.roles.discard(role)


@dataclass
class Game:
    """A class to model the Hundred and Ten game with lobby support"""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = field(default="")
    seed: str = field(default_factory=lambda: str(uuid4()))
    accessibility: Accessibility = field(default=Accessibility.PUBLIC)
    people: PersonGroup = field(default_factory=PersonGroup)

    # The underlying game engine (None until game starts)
    _game: Optional[HundredAndTen] = field(default=None, repr=False)
    # Track all moves made for persistence
    _moves: list[Action] = field(default_factory=list, repr=False)

    @property
    def started(self) -> bool:
        """Check if the game has started"""
        return self._game is not None

    @property
    def moves(self) -> list[Action]:
        """Get all moves made in the game"""
        return self._moves

    @property
    def organizer(self) -> Person:
        """Get the organizer of the game"""
        organizers = self.people.by_role(GameRole.ORGANIZER)
        if organizers:
            return organizers[0]
        # Return a dummy organizer if none exists
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
        if self._game is None:
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
    def rounds(self) -> list[Round]:
        """Get all rounds played"""
        if self._game:
            return list(self._game.rounds)
        return []

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
        if self._game:
            raise ValueError("Cannot join a game that has started")
        if self.accessibility == Accessibility.PRIVATE:
            # Check if invited or already a player
            person = self.people.by_identifier(identifier)
            if not person or GameRole.INVITEE not in person.roles:
                if not person or GameRole.PLAYER not in person.roles:
                    raise ValueError("Cannot join private game without invitation")

        existing = self.people.by_identifier(identifier)
        if existing:
            existing.roles.add(GameRole.PLAYER)
            existing.roles.discard(GameRole.INVITEE)
        else:
            self.people.append(Person(identifier=identifier, roles={GameRole.PLAYER}))

    def leave(self, identifier: str) -> None:
        """Remove a player from the game"""
        if self._game:
            # For active games, automate instead
            self.automate(identifier)
            return
        person = self.people.by_identifier(identifier)
        if person:
            self.people.remove(person)

    def invite(self, inviter: str, invitee: str) -> None:
        """Invite someone to the game"""
        if self._game:
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
            player = self._game.players.by_identifier(identifier)
            if player:
                player.automate = True
                # Trigger automated actions
                self._trigger_automation()

    def start_game(self) -> None:
        """Start the game with current players"""
        if self._game:
            raise ValueError("Game already started")
        if len(self.players) < 2:
            raise ValueError("Need at least 2 players to start")

        # Create players for the game engine
        game_players = Group(
            [Player(identifier=p.identifier, automate=p.automate) for p in self.players]
        )

        # Create the game
        self._game = HundredAndTen(players=game_players, seed=self.seed)

        # Trigger automation for any automated players
        self._trigger_automation()

    def act(self, action: Action) -> None:
        """Perform a game action"""
        if not self._game:
            raise ValueError("Game has not started")
        self._game.act(action)
        # Track the move for persistence
        self._moves.append(action)

    def suggestion(self) -> Action:
        """Get a suggested action"""
        if not self._game:
            raise ValueError("Game has not started")
        return self._game.suggestion()

    def _trigger_automation(self) -> None:
        """Trigger automated actions for automated players"""
        if not self._game:
            return
        # The v2 game handles automation internally
        # But we need to sync automate flags
        for person in self.people:
            if person.automate:
                player = self._game.players.by_identifier(person.identifier)
                if player:
                    player.automate = True
