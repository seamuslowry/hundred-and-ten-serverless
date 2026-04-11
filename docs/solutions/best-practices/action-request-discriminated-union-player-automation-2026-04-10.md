---
title: Use an ActionRequest Discriminated Union for App-Level Player Automation
date: 2026-04-10
category: docs/solutions/best-practices/
module: player_automation
problem_type: best_practice
component: service_object
severity: high
applies_when:
  - A dependency package is split and engine-level polymorphism (e.g. as_engine_player()) can no longer be the dispatch mechanism
  - Player or actor types need to signal different intent (act now, defer, request external automation) without coupling to the engine's type system
  - Queue management or automation side-effects belong at the app/service layer, not inside individual actor implementations
tags:
  - discriminated-union
  - player-automation
  - package-split
  - pattern-matching
  - app-level-dispatch
  - refactoring
  - polymorphism
  - dataclass
---

# Use an ActionRequest Discriminated Union for App-Level Player Automation

## Context

When the `hundredandten` package was split into `hundredandten-engine` and `hundredandten-automation`, the existing player automation design broke at the seam. The old design relied on each player type implementing `as_engine_player()`, which returned an engine-level class (`QueuedActionPlayer`, `EngineNaivePlayer`) that the engine itself knew how to drive. This coupling meant the app layer delegated automation intent down into the engine package — a dependency that became untenable once the engine package no longer contained the automation classes the app expected.

The split forced a clear question: where does the decision of "what should this player do next" actually belong? The answer is the app layer. The engine should receive plain `EnginePlayer` instances and be told what actions to execute; it should not be responsible for deciding whether to pull from a queue, invoke a CPU heuristic, or wait for human input.

## Guidance

**When splitting a game engine package, move player automation intent to an app-level discriminated union rather than engine-level polymorphism.**

Replace the `as_engine_player()` / engine-class polymorphism pattern with an `ActionRequest` discriminated union that each player type returns from a single `next_action()` method. The game object then dispatches on that union in a `match` statement.

**Before — engine-coupled polymorphism:**

```python
# PlayerInGame ABC
def as_engine_player(self) -> EnginePlayer: ...

# Human
def as_engine_player(self) -> EnginePlayer:
    return QueuedActionPlayer(
        self.id,
        queued_actions=deque([a.to_engine() for a in self.queued_actions]),
        on_consume_actions=lambda consumed: setattr(
            self, "queued_actions", self.queued_actions[len(consumed):]
        ),
    )

# NaiveCpu
def as_engine_player(self) -> EnginePlayer:
    return EngineNaivePlayer(self.id)

# Game.__initialize_engine
players=[p.as_engine_player() for p in self.ordered_players]
```

**After — app-level discriminated union:**

```python
# src/models/internal/player.py

@dataclass(frozen=True)
class NoAction:
    """Sentinel: the player has no action to take right now."""

@dataclass(frozen=True)
class ConcreteAction:
    """Wraps a concrete action that should be played immediately."""
    action: Action

@dataclass(frozen=True)
class RequestAutomation:
    """Sentinel: the player defers to automated action resolution (CPU)."""

type ActionRequest = NoAction | ConcreteAction | RequestAutomation

# PlayerInGame ABC — single method replaces three
@abstractmethod
def next_action(self) -> ActionRequest: ...

# Human — FIFO deque
queued_actions: deque[Action] = field(default_factory=deque)

def next_action(self) -> ActionRequest:
    if not self.queued_actions:
        return NoAction()
    return ConcreteAction(self.queued_actions.popleft())

# NaiveCpu
def next_action(self) -> ActionRequest:
    return RequestAutomation()
```

Engine initialization becomes uniform — all players are plain `EnginePlayer`:

```python
def __initialize_engine(self, actions: list[Action]) -> Engine:
    engine = Engine(
        players=[EnginePlayer(p.id) for p in self.ordered_players],
        seed=self.seed,
    )
    for a in actions:
        engine.act(a.to_engine())
    return engine
```

## Why This Matters

**Engine decoupling.** The engine package no longer needs to know anything about queue management or CPU heuristics. It receives plain player identifiers and is told which action to execute. This is the correct direction for a library boundary: the library does what it's told; the application decides what to tell it.

**Single responsibility.** Each player type expresses exactly one thing: what it wants to do next. The `Game` object owns the dispatch logic. Neither the player nor the engine owns the full automation pipeline.

**Exhaustive dispatch.** A `match` statement on a closed union with a wildcard `case _: raise AssertionError(...)` gives static and runtime guarantees that every variant is handled. Adding a new `ActionRequest` variant will produce a type-checker warning at the dispatch site, preventing silent regressions — particularly important for preventing infinite loops in a game automation loop.

**Testability.** Player types become straightforward to unit-test in isolation: construct a `Human` with a pre-loaded deque, call `next_action()`, assert the result. No engine state required.

**O(1) queue operations.** Using `deque` instead of `list` for `Human.queued_actions` makes `popleft()` O(1) rather than O(n), which matters for games with large pre-queued action sequences.

**Guard consolidation.** The old design scattered queue guards across player subclasses (`NaiveCpu.queue_action()` raised `BadRequestError`). The new design centralises the guard in `Game.queue_action_for()` via `isinstance(player, Human)`, making the invariant easy to audit and test.

## When to Apply

- A game engine package is being split and automation classes previously lived inside the engine package.
- Player subclasses implement polymorphic methods that return engine-internal types — a sign that app-level concerns have leaked into the engine boundary.
- The game loop needs to handle heterogeneous player behaviour (human input, CPU heuristics, queued replay) without the engine knowing about the distinction.
- You want exhaustive, type-checked dispatch over player action intent rather than open-ended inheritance.
- Queue management or other per-player side effects are scattered across multiple subclasses and are difficult to audit.
- You are writing tests for player automation and find yourself constructing engine state just to test queue behaviour.

## Examples

**The `_automated_act` dispatch loop:**

```python
def _automated_act(self) -> None:
    while True:
        if self._engine.winner:
            break

        active_player_id = self.active_player_id
        active_player = self.ordered_players.find_or_throw(active_player_id)

        request = active_player.next_action()
        match request:
            case NoAction():
                break
            case ConcreteAction(action):
                engine_action = action.to_engine()
                if engine_action not in self._engine.available_actions(active_player_id):
                    if not isinstance(active_player, Human):
                        raise TypeError(
                            f"Expected Human player for ConcreteAction, "
                            f"got {type(active_player).__name__}"
                        )
                    self._update_game_player(active_player.clear_queued_actions())
                    break
                self._engine.act(engine_action)
            case RequestAutomation():
                naive_act = naive_action_for(self._engine, active_player_id)
                self._engine.act(naive_act)
            case _:
                raise AssertionError(
                    f"Unhandled ActionRequest variant: {request!r}"
                )
```

**Important:** bind the result of `next_action()` to a variable *before* the `match` statement. Calling `active_player.next_action()` inside the `case _` f-string would invoke it a second time — and `Human.next_action()` has a side effect (`deque.popleft()`), so that double-call would silently consume a queued action before raising the error. Binding once and referencing `request` in all arms is both correct and clearer.

Note the wildcard arm. Without it, a future `ActionRequest` variant would cause the loop to spin silently.

**Queue guard consolidated in `Game`:**

```python
def queue_action_for(self, player_id: str, action: Action) -> None:
    player = self.ordered_players.find_or_throw(player_id)
    if not isinstance(player, Human):
        raise BadRequestError("Cannot queue an action for an automated player")
    self._update_game_player(player.queue_action(action))
    self._automated_act()
```

Previously `NaiveCpu` raised this error itself. Moving the guard here means the error policy is defined once, in the object that owns the game state.

**Deserialization — reconstruct as `deque`, not `list`:**

```python
# Broken: queued_actions ends up as list, popleft() unavailable
queued_actions=[__move(move) for move in person.queued_actions]

# Correct:
queued_actions=deque(__move(move) for move in person.queued_actions)
```

When deserializing from a database or JSON representation, the field type on the dataclass (`deque[Action]`) must be honoured explicitly. A list comprehension silently produces the wrong type.

**CPU automation — no redundant round-trip:**

```python
# Before: action went engine → app → engine with no transformation
naive_act = naive_action_for(self._engine, active_player_id)
self._engine.act(ActionFactory.from_engine(naive_act).to_engine())

# After: pass the engine action directly
naive_act = naive_action_for(self._engine, active_player_id)
self._engine.act(naive_act)
```

`naive_action_for` already returns an engine-native action. Converting it to an app action and back added noise without value.

## Related

- `src/models/internal/player.py` — `ActionRequest` union definition; `PlayerInGame` ABC; `Human` and `NaiveCpu` implementations
- `src/models/internal/game.py` — `_automated_act()`, `queue_action_for()`, `clear_queued_actions_for()`, `__initialize_engine()`
- `src/mappers/db/deserialize.py` — `deque` deserialization fix for `Human.queued_actions`
- `tests/models/test_player.py` — unit tests for `next_action()` across all player types
- `tests/functions/test_queued_action.py` — integration tests for queue behaviour and `NaiveCpu` guard
- `docs/plans/2026-04-10-001-refactor-player-automation-api-plan.md` — execution plan for this refactor
