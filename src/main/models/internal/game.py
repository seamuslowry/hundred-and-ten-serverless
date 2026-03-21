"""Model a Hundred and Ten game through its lifecycle (lobby and play phases)."""

from abc import ABC, abstractmethod
from dataclasses import InitVar, dataclass, field
from typing import Optional, Union, override
from uuid import uuid4

from hundredandten import HundredAndTen
from hundredandten.actions import Action
from hundredandten.constants import RoundStatus
from hundredandten.round import Round
from hundredandten.state import GameState

from .constants import Accessibility, GameStatus
from .player import NaiveCpu, PlayerInGame


class PlayerGroup(list[PlayerInGame]):
    """A group of players in a game"""

    def find_or_throw(self, player_id: str) -> PlayerInGame:
        """Find the player with the passed player ID; throw if they don't exist"""
        p = self._by_player_id(player_id)
        if not p:
            raise ValueError(f"Unable to find {player_id}")
        return p

    def find(self, player_id: str) -> Optional[PlayerInGame]:
        """Find the player with the passed player ID; return None if they don't exist"""
        return self._by_player_id(player_id)

    def _by_player_id(self, player_id: str) -> Optional[PlayerInGame]:
        """Find a player by player ID"""
        return next((p for p in self if p.id == player_id), None)


@dataclass
class BaseGame(ABC):
    """Shared fields and properties for Lobby and Game"""

    organizer: PlayerInGame = field()
    players: PlayerGroup = field(default_factory=PlayerGroup)
    id: Optional[str] = field(default=None)
    name: str = field(default="")
    seed: str = field(default_factory=lambda: str(uuid4()))
    accessibility: Accessibility = field(default=Accessibility.PUBLIC)

    @abstractmethod
    def leave(self, player_id: str):
        """Leave the game or the lobby"""

    @property
    def ordered_players(self) -> PlayerGroup:
        """The canonical order of all players in this game"""
        return PlayerGroup([self.organizer, *self.players])


@dataclass
class Lobby(BaseGame):
    """A class to model the lobby phase of a Hundred and Ten game"""

    invitees: PlayerGroup = field(default_factory=PlayerGroup)

    def join(self, player: PlayerInGame) -> None:
        """Add a player to the lobby"""
        if self.accessibility == Accessibility.PRIVATE and not self.invitees.find(
            player.id
        ):
            raise ValueError("Cannot join private game without invitation")

        self.players.append(player)

    def leave(self, player_id: str) -> None:
        """Remove a player from the lobby"""
        if player_id == self.organizer.id:
            raise ValueError("Organizer cannot leave a lobby")

        self.players.remove(self.players.find_or_throw(player_id))

    def invite(self, inviter: str, invitee: PlayerInGame) -> None:
        """Invite someone to the game"""
        if self.organizer.id != inviter and self.players.find(inviter) is None:
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
        return Game(
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
    def winner(self) -> Optional[PlayerInGame]:
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
    def leave(self, player_id: str) -> None:
        """Automate a player (used when leaving an active game)"""
        self._update_game_player(NaiveCpu(player_id))

    def act(self, action: Action) -> None:
        """Perform a game action"""
        self._game.act(action)

    def queue_action_for(self, player_id: str, action: Optional[Action]) -> None:
        """Queue an action for a player"""
        self._update_game_player(
            self.ordered_players.find_or_throw(player_id).queue_action(action)
        )

    def _update_game_player(self, new_player: PlayerInGame):
        """Update a game player and re-initialize the engine with that player"""
        original_player = self.ordered_players.find_or_throw(new_player.id)

        if original_player == self.organizer:
            self.organizer = new_player
        else:
            self.players[self.players.index(original_player)] = new_player

        self._game = self._initialize_game(self.moves)

    def game_state_for(self, player_id: str) -> GameState:
        """Return the game state known for a particular player"""
        return self._game.game_state_for(player_id)

    def _initialize_game(self, moves: list[Action]) -> HundredAndTen:
        return HundredAndTen(
            players=[p.as_engine_player() for p in self.ordered_players],
            seed=self.seed,
            initial_moves=moves,
        )
