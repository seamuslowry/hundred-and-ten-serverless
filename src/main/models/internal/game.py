"""Model a Hundred and Ten game through its lifecycle (lobby and play phases)."""

from abc import ABC, abstractmethod
from dataclasses import InitVar, dataclass, field
from itertools import chain
from typing import Optional, override
from uuid import uuid4

from hundredandten import HundredAndTen
from hundredandten.actions import (
    Play as EnginePlay,
)
from hundredandten.deck import Card as EngineCard
from hundredandten.player import NaiveAutomatedPlayer

from src.main.mappers.engine import deserialize, serialize

from .actions import Action, Card, Event, GameEnd, GameStart, Play
from .constants import Accessibility, CardNumber, CardSuit, GameStatus
from .player import NaiveCpu, PlayerInGame, PlayerInRound
from .trick import Trick


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

    initial_actions: InitVar[Optional[list[Action]]] = None

    # The underlying game engine (always exists for a Game)
    _game: HundredAndTen = field(init=False, repr=False)

    _actions: list[Action] = field(init=False, repr=False, default_factory=list)

    def __post_init__(self, initial_moves: Optional[list[Action]]):
        self._game = self._initialize_game(initial_moves or [])
        self._actions = [deserialize.action(a) for a in self._game.moves]

    @staticmethod
    def from_lobby(lobby: Lobby) -> "Game":
        """Create a Game from a Lobby (starts the game)"""
        return Game(
            id=lobby.id,
            name=lobby.name,
            seed=lobby.seed,
            accessibility=lobby.accessibility,
            organizer=lobby.organizer,
            players=lobby.players,
            initial_actions=[],
        )

    @property
    def actions(self) -> list[Action]:
        """Get all moves made in the game"""
        return self._actions

    @property
    def status(self) -> GameStatus:
        """Get the current game status"""
        if self._game.winner:
            return GameStatus.WON
        return GameStatus[self._game.active_round.status.name]

    @property
    def winner(self) -> Optional[PlayerInGame]:
        """Get the winner of the game"""
        if self._game.winner:
            return self.ordered_players.find_or_throw(self._game.winner.identifier)
        return None

    @property
    def active_player_id(self) -> str:
        """Get the current active player ID"""
        return self._game.active_round.active_player.identifier

    @property
    def dealer_player_id(self) -> str:
        """Get the current dealer player ID"""
        return self._game.active_round.dealer.identifier

    @property
    def bidder_player_id(self) -> Optional[str]:
        """Get the current bidding player ID"""
        return (
            self._game.active_round.active_bidder.identifier
            if self._game.active_round.active_bidder
            else None
        )

    @property
    def active_bid(self) -> Optional[int]:
        """Get the current bidding player ID"""
        return (
            self._game.active_round.active_bid.value
            if self._game.active_round.active_bid
            else None
        )

    @property
    def trump(self) -> Optional[CardSuit]:
        """Get the selected trump"""
        return (
            CardSuit[self._game.active_round.trump.name]
            if self._game.active_round.trump
            else None
        )

    @property
    def current_round_tricks(self) -> list[Trick]:
        """The tricks in the current round"""
        return [
            Trick(
                bleeding=t.bleeding,
                plays=[self.__convert_engine_play(p) for p in t.plays],
                winning_play=(
                    self.__convert_engine_play(t.winning_play)
                    if t.winning_play
                    else None
                ),
            )
            for t in self._game.active_round.tricks
        ]

    @property
    def events(self) -> list[Event]:
        """Get all game events"""

        return [
            GameStart(),
            *chain.from_iterable(
                deserialize.round_events(r) for r in self._game.rounds
            ),
            *([] if not self.winner else [GameEnd(self.winner.id)]),
        ]

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
        # TODO: this is a hack. the library should return this value
        initial = len(self._game.moves)
        self._game.act(serialize.action(action))
        # TODO: act needs to return all the actions that occured as part of this action
        # _those_ should be appended to the internal actions array
        self._actions.extend([deserialize.action(a) for a in self._game.moves[initial:]])

    def get_player_in_round(self, player_id: str) -> PlayerInRound:
        """Return the representation of this player as they are in the round"""
        return PlayerInRound(
            id=player_id,
            hand=[
                self.__convert_engine_card(c)
                for c in next(
                    p
                    for p in self._game.active_round.players
                    if p.identifier == player_id
                ).hand
            ],
        )

    def queue_action_for(self, player_id: str, action: Action) -> None:
        """Queue an action for a player"""
        self._update_game_player(
            self.ordered_players.find_or_throw(player_id).queue_action(action)
        )

    def clear_queued_actions_for(self, player_id: str) -> None:
        """Clear all queued actions for a player"""
        self._update_game_player(
            self.ordered_players.find_or_throw(player_id).clear_queued_actions()
        )

    def _update_game_player(self, new_player: PlayerInGame):
        """Update a game player and re-initialize the engine with that player"""
        original_player = self.ordered_players.find_or_throw(new_player.id)

        if original_player == self.organizer:
            self.organizer = new_player
        else:
            self.players[self.players.index(original_player)] = new_player

        self._game = self._initialize_game(self.actions)

    def suggestion_for(self, player_id: str) -> Action:
        """Return a suggested action for the given player"""
        return deserialize.action(
            NaiveAutomatedPlayer(player_id).act(self._game.game_state_for(player_id))
        )

    def _initialize_game(self, actions: list[Action]) -> HundredAndTen:
        return HundredAndTen(
            players=[p.as_engine_player() for p in self.ordered_players],
            seed=self.seed,
            initial_moves=[serialize.action(m) for m in (actions or [])],
        )

    def __convert_engine_card(self, c: EngineCard) -> Card:
        return Card(suit=CardSuit[c.suit.name], number=CardNumber(c.number.name))

    def __convert_engine_play(self, p: EnginePlay) -> Play:
        return Play(player_id=p.identifier, card=self.__convert_engine_card(p.card))
