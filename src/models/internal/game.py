"""Model a Hundred and Ten game through its lifecycle (lobby and play phases)."""

from abc import ABC, abstractmethod
from dataclasses import InitVar, dataclass, field
from typing import Optional, override
from uuid import uuid4

from hundredandten.automation import naive
from hundredandten.automation.engineadapter import EngineAdapter, UnavailableActionError
from hundredandten.engine import Game as Engine, Player as EnginePlayer
from hundredandten.engine.round import Round as EngineRound

from .actions import (
    Action,
    ActionFactory,
    Bid,
    Card,
    Event,
    GameEnd,
    GameStart,
    Play,
    RoundEnd,
    RoundStart,
    TrickEnd,
    TrickStart,
)
from .constants import Accessibility, CardSuit, GameStatus
from .errors import BadRequestError, InternalServerError
from .player import (
    ConcreteAction,
    Human,
    NaiveCpu,
    NoAction,
    PlayerInGame,
    PlayerInRound,
    RequestAutomation,
)
from .round import Round
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
    _engine: Engine = field(init=False, repr=False)

    def __post_init__(self, initial_actions: Optional[list[Action]]):
        self.__initialize_engine(initial_actions or [])

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
        return list(ActionFactory.from_engine(a) for a in self._engine.actions)

    @property
    def status(self) -> GameStatus:
        """Get the current game status"""
        if self._engine.winner:
            return GameStatus.WON
        return GameStatus[self._engine.active_round.status.name]

    @property
    def winner(self) -> Optional[PlayerInGame]:
        """Get the winner of the game"""
        if self._engine.winner:
            return self.ordered_players.find_or_throw(self._engine.winner.identifier)
        return None

    @property
    def active_player_id(self) -> str:
        """Get the current active player ID"""
        return self._engine.active_player.identifier

    @property
    def dealer_player_id(self) -> str:
        """Get the current dealer player ID"""
        return self._engine.active_round.dealer.identifier

    @property
    def bidder_player_id(self) -> Optional[str]:
        """Get the current bidding player ID"""
        return (
            self._engine.active_round.active_bidder.identifier
            if self._engine.active_round.active_bidder
            else None
        )

    @property
    def active_bid(self) -> Optional[int]:
        """Get the current bidding player ID"""
        return (
            self._engine.active_round.active_bid.value
            if self._engine.active_round.active_bid
            else None
        )

    @property
    def trump(self) -> Optional[CardSuit]:
        """Get the selected trump"""
        return (
            CardSuit[self._engine.active_round.trump.name]
            if self._engine.active_round.trump
            else None
        )

    @property
    def current_round_tricks(self) -> list[Trick]:
        """The tricks in the current round"""
        return [
            Trick(
                bleeding=t.bleeding,
                plays=[Play.from_engine(p) for p in t.plays],
                winning_play=(
                    Play.from_engine(t.winning_play) if len(t.plays) else None
                ),
            )
            for t in self._engine.active_round.tricks
        ]

    @property
    def events(self) -> list[Event]:
        """Get all game events via action-walking replay"""
        replay_engine = Engine(
            players=[EnginePlayer(p.id) for p in self.ordered_players],
            seed=self.seed,
        )

        return [
            GameStart(),
            RoundStart(
                dealer=replay_engine.active_round.dealer.identifier,
                hands={
                    p.identifier: [Card.from_engine(c) for c in p.hand]
                    for p in replay_engine.active_round.players
                },
            ),
            *(
                event
                for a in self.actions
                for event in Game.__events_for_action(replay_engine, a)
            ),
            *(
                [GameEnd(winner=replay_engine.winner.identifier)]
                if replay_engine.winner
                else []
            ),
        ]

    @staticmethod
    def __events_for_action(replay_engine: Engine, action: Action) -> list[Event]:
        before_action_round_count = len(replay_engine.rounds)
        before_action_trick_count = len(replay_engine.active_round.tricks)

        replay_engine.act(action.to_engine())

        after_action_round_count = len(replay_engine.rounds)
        after_action_trick_count = len(replay_engine.active_round.tricks)

        return [
            # always include the action itself
            action,
            # if the action resulted in an ended trick, include TrickEnd
            *(
                [
                    TrickEnd(
                        winner=(
                            replay_engine.active_round.tricks[-2]
                            if replay_engine.active_round.tricks
                            else replay_engine.rounds[-2].tricks[-1]
                        ).winning_play.identifier
                    )
                ]
                if before_action_trick_count > 0
                and after_action_trick_count != before_action_trick_count
                else []
            ),
            # if the action resulted in starting a trick, include TrickStart
            *(
                [TrickStart()]
                if after_action_trick_count > before_action_trick_count
                else []
            ),
            # if the action ended a round, include RoundEnd
            *(
                [
                    RoundEnd(
                        scores={
                            s.identifier: s.value
                            for s in replay_engine.rounds[-2].scores
                        }
                    )
                ]
                if after_action_round_count > before_action_round_count
                or replay_engine.winner is not None
                else []
            ),
            # if the action started a new round, include RoundStart
            *(
                [
                    RoundStart(
                        dealer=replay_engine.active_round.dealer.identifier,
                        hands={
                            p.identifier: [Card.from_engine(c) for c in p.hand]
                            for p in replay_engine.active_round.players
                        },
                    )
                ]
                if after_action_round_count > before_action_round_count
                else []
            ),
        ]

    def __get_round_at(self, round_index: int) -> Round:
        game_round = self._engine.rounds[round_index]

        round_scores = {}

        for score in game_round.scores:
            round_scores[score.identifier] = (
                round_scores.get(score.identifier, 0) + score.value
            )

        # cheat and get initial hands by recreating the start of the round
        recreated_round = EngineRound(
            game_players=[EnginePlayer(p.identifier) for p in game_round.players],
            dealer_identifier=game_round.dealer.identifier,
            seed=game_round.seed,
        )

        return Round(
            dealer_player_id=game_round.dealer.identifier,
            trump=CardSuit[game_round.trump.name] if game_round.trump else None,
            initial_hands={
                p.identifier: [Card.from_engine(c) for c in p.hand]
                for p in recreated_round.players
            },
            bid_history=[Bid.from_engine(b) for b in game_round.bids],
            discards={
                d.identifier: [Card.from_engine(c) for c in d.cards]
                for d in game_round.discards
            },
            tricks=[
                Trick(
                    bleeding=t.bleeding,
                    plays=[Play.from_engine(p) for p in t.plays],
                    winning_play=(
                        # TODO: test for serialization when trick is just starting
                        Play.from_engine(t.winning_play) if len(t.plays) else None
                    ),
                )
                for t in game_round.tricks
            ],
            scores=round_scores,
        )

    @property
    def rounds(self) -> list[Round]:
        """Get all rounds as structured objects via direct engine inspection"""

        return [self.__get_round_at(i) for i in range(len(self._engine.rounds))]

    @property
    def scores(self) -> dict[str, int]:
        """Get current scores"""
        return self._engine.scores

    @override
    def leave(self, player_id: str) -> None:
        """Automate a player (used when leaving an active game)"""
        self._update_game_player(NaiveCpu(player_id))

    def act(self, action: Action) -> None:
        """Perform a game action"""
        self._engine.act(action.to_engine())

        self.__automated_act()

    def __automated_act(self) -> None:
        while (
            not self.winner
            and (
                active_player := self.ordered_players.find_or_throw(
                    self.active_player_id
                )
            )
            is not None
            and (action_request := active_player.next_action()) != NoAction()
        ):
            match action_request:
                case ConcreteAction(action):
                    try:
                        self._engine.act(
                            EngineAdapter.action_for(
                                self._engine,
                                active_player.id,
                                lambda _: EngineAdapter.available_action_from_engine(
                                    action.to_engine()
                                ),
                            )
                        )
                    except UnavailableActionError:
                        assert isinstance(active_player, Human), (
                            "Only Human players produce ConcreteAction; "
                            f"got {active_player}"
                        )
                        self._update_game_player(active_player.clear_queued_actions())
                case RequestAutomation():
                    self._engine.act(
                        EngineAdapter.action_for(
                            self._engine,
                            active_player.id,
                            naive.action_for,
                        )
                    )
                case _:  # pragma: no cover
                    # type: ignore[unreachable]
                    raise InternalServerError(
                        f"Unable to process action request. Automation failing for {action_request}"
                    )

    def get_player_in_round(self, player_id: str) -> PlayerInRound:
        """Return the representation of this player as they are in the round"""
        return PlayerInRound(
            id=player_id,
            hand=[
                Card.from_engine(c)
                for c in next(
                    p
                    for p in self._engine.active_round.players
                    if p.identifier == player_id
                ).hand
            ],
        )

    def queue_action_for(self, player_id: str, action: Action) -> None:
        """Queue an action for a player"""
        player = self.ordered_players.find_or_throw(player_id)
        if not isinstance(player, Human):
            raise BadRequestError("Cannot queue an action for an automated player")
        self._update_game_player(player.queue_action(action))

    def clear_queued_actions_for(self, player_id: str) -> None:
        """Clear all queued actions for a player"""
        player = self.ordered_players.find_or_throw(player_id)
        if not isinstance(player, Human):
            raise BadRequestError("Cannot queue actions for an automated player")
        self._update_game_player(player.clear_queued_actions())

    def _update_game_player(self, new_player: PlayerInGame):
        """Update a game player and re-initialize the engine with that player"""
        original_player = self.ordered_players.find_or_throw(new_player.id)

        if original_player == self.organizer:
            self.organizer = new_player
        else:
            self.players[self.players.index(original_player)] = new_player

        self.__initialize_engine(self.actions)

    def suggestions_for(self, player_id: str) -> list[Action]:
        """Return a list of suggested actions for the given player"""
        try:
            return [
                ActionFactory.from_engine(
                    EngineAdapter.action_for(
                        self._engine,
                        player_id,
                        naive.action_for,
                    )
                )
            ]
        except UnavailableActionError:
            return []  # if no suggestion is available, return an empty list

    def __initialize_engine(self, actions: list[Action]) -> None:
        self._engine = Engine(
            players=[EnginePlayer(p.id) for p in self.ordered_players],
            seed=self.seed,
        )

        for a in actions:
            self._engine.act(a.to_engine())

        self.__automated_act()
