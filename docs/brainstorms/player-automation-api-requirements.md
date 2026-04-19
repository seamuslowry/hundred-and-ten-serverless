---
date: 2026-04-10
topic: player-automation-api
---

# Player Automation API

## Problem Frame

The codebase is mid-refactor after splitting the game logic into two packages:
`hundredandten-engine` (pure rules) and `hundredandten-automation` (AI decisions).
The `NaiveCpu` player has a stub `pop_action()` that returns `None`, meaning CPU
players never actually take automated turns. The underlying tension is that
`PlayerInGame` is engine-agnostic by design, but a CPU player needs engine state to
decide its next move. Additionally, `queue_action` / `clear_queued_actions` exist on
the base class even though they are meaningless for any automated player — they
currently raise `BadRequestError` on `NaiveCpu`, which pushes validation responsibility
onto callers. The goal is a clean, generic API for obtaining the next action from any
player type, with correct behavior for both humans (queued actions) and all current and
future CPU types.

## Requirements

**`PlayerInGame` interface**

- R1. `PlayerInGame` exposes a single abstract method `next_action() -> ActionRequest`
  where `ActionRequest` is a discriminated union of three variants:
  - `NoAction` — no action is ready (human has nothing queued, or it is not this
    player's turn)
  - `ConcreteAction(action: Action)` — a specific action is ready to play immediately
  - `RequestAutomation` — the player delegates to the game engine's automation layer
    to compute the action
- R2. `queue_action(action)` and `clear_queued_actions()` are **removed from
  `PlayerInGame`**. They are not part of the generic player contract.

**`Human` player**

- R3. `Human.next_action()` returns `ConcreteAction` with the next item from
  `queued_actions` if the queue is non-empty, or `NoAction` if empty. The deque pop
  semantics (FIFO/LIFO) remain as-is.
- R4. `Human` retains `queue_action(action)` and `clear_queued_actions()` as concrete
  methods on the class directly (not via the base interface).

**CPU players**

- R5. `NaiveCpu.next_action()` returns `RequestAutomation` unconditionally.
- R6. Future CPU player types (e.g., `SmartCpu`) follow the same pattern: return
  `RequestAutomation` from `next_action()`. The automation function used to resolve it
  is determined by `Game`, not by the player.
- R7. CPU players do not implement `queue_action` or `clear_queued_actions`.

**`Game` automation loop**

- R8. `Game.__automated_act()` calls `player.next_action()` and dispatches on the
  result:
  - `NoAction` → stop the loop
  - `ConcreteAction(action)` → validate against `available_actions`; if valid, call
    `engine.act(action)`; if invalid, call `player.clear_queued_actions()` and stop
  - `RequestAutomation` → call `naive_action_for(self._engine, player_id)` and
    immediately pass the result to `engine.act()`; continue the loop
- R9. The loop continues after a `RequestAutomation` resolution to allow chained
  automated turns (e.g., multiple CPU players in sequence). It stops only on `NoAction`
  or an invalid `ConcreteAction`.
- R10. `Game.queue_action_for()` and `Game.clear_queued_actions_for()` type-narrow to
  `Human` before calling `queue_action` / `clear_queued_actions`, since those methods
  no longer exist on the base class. Attempts to queue an action for a non-`Human`
  player should raise `BadRequestError` at the `Game` layer.

**`ActionRequest` type**

- R11. `ActionRequest` and its three variants (`NoAction`, `ConcreteAction`,
  `RequestAutomation`) are defined in `src/models/internal/player.py` alongside the
  player classes.
- R12. `RequestAutomation` carries no data — it is a sentinel. A module-level singleton
  or a zero-field dataclass are both acceptable; the choice is deferred to planning.

## Success Criteria

- `NaiveCpu` players take automated turns during `__automated_act()` without requiring
  engine state to be stored on the player object.
- Human pre-queued actions continue to work as before: queued before their turn,
  consumed in order during `__automated_act()`, flushed on invalid action.
- Adding a new CPU player type requires only: implementing `next_action()` returning
  `RequestAutomation` and no queue methods. No changes to `Game` are needed unless a
  different automation function is required.
- All existing tests pass. The suggestion endpoint (`game.suggestion_for()`) is
  unaffected — it calls `naive_action_for` directly and does not go through
  `next_action()`.

## Scope Boundaries

- The automation function used to resolve `RequestAutomation` is always
  `naive_action_for` from `hundredandten-automation`. Routing different CPU types to
  different automation functions is a future concern, not in scope here.
- No changes to the action types (`Bid`, `Play`, `Discard`, `SelectTrump`), their
  `to_engine()` / `from_engine()` converters, or the client/DB serialization layers.
- The commented-out `QueuedActionPlayer` / `EngineAutomatedPlayer` approach is
  explicitly out of scope. That design pushed automation into the engine layer; this
  approach keeps it in `Game`.
- No changes to API routes, request/response models, or MongoDB storage format.

## Key Decisions

- **Sentinel over callable injection**: `RequestAutomation` keeps players engine-free.
  `Game` owns all automation wiring. Callable injection (Approach B) was rejected
  because it requires the callable to capture a mutable engine reference and be
  refreshed after every `__initialize_engine` call.
- **Queue methods removed from base interface**: Only `Human` will ever support
  queuing. Keeping them on the base class was misleading and required CPU players to
  raise `BadRequestError`. Callers that need to queue type-narrow to `Human`.
- **`next_action()` over `pop_action()`**: The new name reflects that the method may
  not consume state (CPU players have no queue to pop) and returns a richer result than
  an optional action.

## Dependencies / Assumptions

- `hundredandten-automation.naive_action_for(engine, player_id)` is already integrated
  and functional (used by `game.suggestion_for()`). No changes to the automation
  package are required.
- `Game.__automated_act()` already has access to `self._engine` and
  `self.active_player_id`, so resolving `RequestAutomation` requires no structural
  change to `Game`'s data model.

## Outstanding Questions

### Deferred to Planning

- [Affects R12][Technical] Should `RequestAutomation` be a module-level singleton
  instance or a zero-field frozen dataclass? Either works; the choice affects
  `isinstance` checks vs. identity comparisons in `__automated_act()`.
- [Affects R9][Technical] Is it possible for `naive_action_for` to return `None` (e.g.,
  no legal moves for the CPU player)? If so, the loop needs a guard against infinite
  recursion or a `None` result from automation. Verify the automation package's contract
  and add a guard if needed.
- [Affects R8][Technical] After `clear_queued_actions()` is called for an invalid
  `ConcreteAction`, should the loop attempt `next_action()` again (in case the player
  has more queued items) or stop? Current behavior stops; confirm this is the intended
  semantics before implementing.

## Next Steps

-> `/ce:plan` for structured implementation planning
