"""Model the lobby phase of a Hundred and Ten game."""

from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4

from utils.constants import Accessibility, GameRole
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


@dataclass
class Lobby(BaseGame):
    """A class to model the lobby phase of a Hundred and Ten game"""

    def join(self, identifier: str) -> None:
        """Add a player to the lobby"""
        person = self.people.by_identifier(identifier)

        if self.accessibility == Accessibility.PRIVATE:
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
        """Remove a player from the lobby"""
        person = self.people.by_identifier(identifier)
        if person:
            self.people.remove(person)

    def invite(self, inviter: str, invitee: str) -> None:
        """Invite someone to the game"""
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
