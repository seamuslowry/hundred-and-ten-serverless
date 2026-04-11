---
title: "refactor: Introduce ActionRequest discriminated union for player automation"
type: refactor
status: completed
date: 2026-04-10
origin: docs/brainstorms/player-automation-api-requirements.md
---

# refactor: Introduce ActionRequest discriminated union for player automation

## Overview

Replace the three-method `PlayerInGame` abstract interface (`pop_action`, `queue_action`,
`clear_queued_actions`) with a single `next_action() -> ActionRequest` method, where
`ActionRequest` is a discriminated union of `NoAction | ConcreteAction | RequestAutomation`.
`Human` keeps its queue methods as concrete instance methods (not via the base class).
`NaiveCpu.next_action()` returns `RequestAutomation` unconditionally. `Game.__automated_act()`
dispatches on the union, calling `naive_action_for(self._engine, player_id)` to resolve CPU turns.

This unblocks the `hundredandten-engine` / `hundredandten-automation` package split and makes
CPU players actually take automated turns during game play.

## Problem Frame

`NaiveCpu.pop_action()` is a stub returning `None` — CPU players never act automatically.
The root tension is that `PlayerInGame` is engine-agnostic, but computing a CPU action requires
engine state. The sentinel approach keeps players engine-free: CPU players declare intent
(`RequestAutomation`), and `Game` resolves it. Queue methods on the base class were misleading
because CPU players raise `BadRequestError` on them; removing them from the interface tightens
the contract.

See origin: `docs/brainstorms/player-automation-api-requirements.md`

## Requirements Trace

- R1. `PlayerInGame` exposes `next_action() -> ActionRequest` (union of `NoAction`, `ConcreteAction`, `RequestAutomation`)
- R2. `queue_action` and `clear_queued_actions` removed from `PlayerInGame` base
- R3. `Human.next_action()` returns `ConcreteAction` from queue or `NoAction` if empty
- R4. `Human` retains `queue_action` and `clear_queued_actions` as direct concrete methods
- R5. `NaiveCpu.next_action()` returns `RequestAutomation` unconditionally
- R6. Future CPU types return `RequestAutomation`; `Game` owns automation wiring
- R7. CPU players do not implement queue methods
- R8. `Game.__automated_act()` dispatches on `ActionRequest`
- R9. Loop continues after `RequestAutomation` to chain CPU turns; stops on `NoAction` or invalid `ConcreteAction`
- R10. `Game.queue_action_for()` and `Game.clear_queued_actions_for()` type-narrow to `Human`, raising `BadRequestError` for other player types. The `clear_queued_actions()` call inside `__automated_act()` on the invalid-action path is a **third type-narrowing site** — the player there is always `Human` by invariant; annotate with `assert isinstance(active_player, Human)` before calling.
- R11. `ActionRequest` and variants defined in `src/models/internal/player.py`
- R12. `RequestAutomation` is a zero-field frozen dataclass sentinel

**Additional resolution from planning:**
- Queue pop semantics: fix `deque.pop()` → `deque.popleft()` (FIFO). Pre-existing LIFO bug; fix during rename.
- WON-state guard: `__automated_act()` must break when `self._engine.winner` is truthy to prevent `StopIteration` crash when a CPU chain ends the game.
- Invalid-action clear: the `clear_queued_actions()` call at the invalid-action site in `__automated_act()` must also type-narrow to `Human` (the player at that site is always a `Human` by invariant, but the static type is `PlayerInGame`).

## Scope Boundaries

- Automation always resolves via `naive_action_for` from `hundredandten-automation`; routing different CPU types to different functions is future work
- No changes to action types, `to_engine()` / `from_engine()` converters, or client/DB serialization
- The commented-out `QueuedActionPlayer` / `EngineAutomatedPlayer` design is explicitly excluded
- No API route, request/response model, or MongoDB schema changes

## Context & Research

### Relevant Code and Patterns

- **`src/models/internal/player.py`** — `PlayerInGame` ABC (lines 48–64), `Human` (67–96), `NaiveCpu` (99–111)
- **`src/models/internal/game.py`** — `__automated_act` (225–239), `act` (219–223), `queue_action_for` (255–260), `clear_queued_actions_for` (262–266), `_update_game_player` (268–277), `__initialize_engine` (332–341)
- **`src/models/internal/actions.py`** — `type Action = Union[Bid, SelectTrump, Discard, Play]` (line 128); Python 3.12 soft-alias `type` syntax used throughout
- **`src/mappers/db/serialize.py`** — `__player_in_game()` dispatches via `match` on `Human`/`NaiveCpu` (lines 58–63); accesses `person.queued_actions` as a field, not a method — unaffected
- **`src/mappers/client/serialize.py`** — already guards with `isinstance(player_in_game, internal.Human)` (line 143) before accessing `queued_actions` — unaffected
- **`tests/mappers/test_mapper_edge_cases.py`** — `UnknownPerson(PlayerInGame)` stub (lines 19–43) implements all three abstract methods; must be updated to implement only `next_action()`
- **`src/models/internal/game.py` line 9** — `from hundredandten.automation import naive_action_for` already imported; used in `suggestion_for()` (line 281)
- **Dispatch pattern:** `match` / `case` is used in `serialize.py` and `deserialize.py`; prefer `match` for dispatching on `ActionRequest` variants in `__automated_act()`
- **`@dataclass(frozen=True)`** pattern used for existing action types — use the same for `RequestAutomation`

### Institutional Learnings

- **`docs/solutions/test-failures/silent-assert-and-wrong-slice-in-test-helpers-2026-04-09.md`**: Always prefix `contains_unsequenced()` with `assert`. After any helper refactor, grep for bare predicate calls and module-level constants (e.g., `DEFAULT_ID`) inside helpers that accept the same concept as a parameter.
- **`docs/solutions/logic-errors/queue-action-hardcoded-player-id-assertion-2026-04-09.md`**: After structural refactor, audit every assertion dict in test helpers for hardcoded constants. Add return type annotations to all helpers.
- **General**: Consider using `typing.assert_never` on the unreachable branch of `ActionRequest` dispatch to provide exhaustiveness checking.

### External References

None — all patterns are well-established in this codebase. No external research needed.

## Key Technical Decisions

- **`RequestAutomation` as a zero-field frozen dataclass**: Enables `match case RequestAutomation()` dispatch (consistent with `match` style used elsewhere in the codebase) and `isinstance` checks. A singleton would work but `match` pattern matching on a frozen dataclass is idiomatic Python 3.12+. (see origin R12)
- **Queue methods removed from `PlayerInGame` base**: Only `Human` will ever support queuing. Keeping them on the base forced CPU players to raise from abstract implementations. Callers that need to queue type-narrow to `Human` explicitly. (see origin R2)
- **`Game` owns automation wiring, not `PlayerInGame`**: Players declare intent via `RequestAutomation`; `Game.__automated_act()` calls `naive_action_for`. This avoids engine coupling in players. (see origin, Key Decisions)
- **WON-state guard added to loop**: A CPU automation chain can now play the game to completion in a single `__automated_act()` call. Without a guard, `self.active_player_id` raises `StopIteration` when the engine is in a won state. Guard added: check `self._engine.winner` at the start of each loop iteration.
- **Fix LIFO → FIFO**: `Human.pop_action()` used `deque.pop()` (LIFO). Rename to `next_action()` + fix to `deque.popleft()` (FIFO). The rename makes this the natural moment to fix the semantic mismatch.
- **Type-narrow `clear_queued_actions()` in invalid-action branch**: The call at `game.py:236` is on the player whose `ConcreteAction` was rejected — always a `Human` by invariant, but statically `PlayerInGame`. Must assert/narrow before calling since the method no longer exists on the base.

## Open Questions

### Resolved During Planning

- **`RequestAutomation` singleton vs dataclass?**: Use a zero-field `@dataclass(frozen=True)`. Enables `match case RequestAutomation()` dispatch consistent with the codebase's `match`/`case` style.
- **Can `naive_action_for` return `None`?**: Already used in `suggestion_for()` without a `None` guard; `ActionFactory.from_engine()` would raise on `None`. Treat the automation package's contract as: always returns a valid action for a legal game state. No guard needed, but the WON-state check at the loop top prevents calling it on a finished game.
- **Should the loop attempt `next_action()` again after an invalid `ConcreteAction` clear?**: No — current behavior stops after flush; preserve this. After calling `clear_queued_actions()`, `break` the loop. Do not `continue` — an extra iteration is unnecessary and could trigger the WON-state guard or other side effects on a loop that should have already stopped.
- **Queue order (LIFO vs FIFO)?**: Fix to FIFO (`popleft()`) as part of this rename. Pre-existing bug; the rename is the right moment.

### Deferred to Implementation

- **Exact `match` / `isinstance` pattern for `ActionRequest` dispatch in `__automated_act()`**: Either `match result: case NoAction(): ...` or `if isinstance(result, NoAction)` chains are valid. Implementer should follow whichever is cleaner given the full method body.
- **Whether `assert_never` for exhaustiveness is worth adding on the `else` branch**: Low risk, high future-proofing. Implementer's call.
- **Whether `naive_action_for` result should be validated against `available_actions` in debug mode**: Not required by spec; implementer may add an `assert` for development confidence.

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

### `ActionRequest` type shape

```
# Three variants, all zero- or one-field frozen dataclasses
NoAction           # empty — nothing to do
ConcreteAction     # wraps a single Action — play this
RequestAutomation  # empty sentinel — ask the engine for a move
```

### `__automated_act` dispatch logic (after refactor)

```
loop:
  if game is won → break

  player = active player
  match player.next_action():
    NoAction          → break
    ConcreteAction(a) → if a not in available_actions:
                            narrow player to Human, clear_queued_actions(), break
                        else:
                            engine.act(a), continue
    RequestAutomation → naive_act = naive_action_for(engine, player_id)
                        engine.act(naive_act), continue
```

### Interface change summary

```
Before                          After
──────────────────────────────  ──────────────────────────────────────────
PlayerInGame (ABC)              PlayerInGame (ABC)
  pop_action() → Optional[A]     next_action() → ActionRequest
  queue_action(a) → Self         (removed)
  clear_queued_actions() → Self  (removed)

Human(PlayerInGame)             Human(PlayerInGame)
  pop_action() → Optional[A]     next_action() → ActionRequest
  queue_action(a) → Self         queue_action(a) → Self   (direct, not ABC)
  clear_queued_actions() → Self  clear_queued_actions() → Self  (direct)

NaiveCpu(PlayerInGame)          NaiveCpu(PlayerInGame)
  pop_action() → None            next_action() → RequestAutomation()
  queue_action → raises          (removed)
  clear_queued_actions → raises  (removed)
```

## Implementation Units

- [ ] **Unit 1: Define `ActionRequest` union and variants**

**Goal:** Introduce the `ActionRequest` discriminated union and its three variants alongside the player classes.

**Requirements:** R1, R11, R12

**Dependencies:** None

**Files:**
- Modify: `src/models/internal/player.py`

**Approach:**
- Add three `@dataclass(frozen=True)` types: `NoAction`, `ConcreteAction` (with one field **named `action`** of type `Action` — the field name matters because `case ConcreteAction(action):` in a `match` block destructures by `__match_args__` order), `RequestAutomation` (zero fields)
- Add `type ActionRequest = NoAction | ConcreteAction | RequestAutomation` soft-alias (Python 3.12 `type` syntax, consistent with `type Action = ...` in `actions.py`)
- Place the new types above the player class definitions in the same file

**Patterns to follow:**
- `type Action = Union[Bid, SelectTrump, Discard, Play]` in `src/models/internal/actions.py` (line 128) — same `type` alias syntax
- Existing `@dataclass` style throughout `src/models/internal/`

**Test scenarios:**
- Test expectation: none — pure type definitions with no behavior; covered implicitly by Unit 2 and Unit 3 tests

**Verification:**
- `pyright` passes with no new errors on `src/models/internal/player.py`
- The three variant types are importable from `src.models.internal.player`

---

- [ ] **Unit 2: Refactor `PlayerInGame`, `Human`, and `NaiveCpu`**

**Goal:** Replace the three-method ABC with `next_action()`; keep queue methods on `Human` only; fix LIFO → FIFO; implement `NaiveCpu.next_action()`.

**Requirements:** R1, R2, R3, R4, R5, R6, R7

**Dependencies:** Unit 1

**Files:**
- Modify: `src/models/internal/player.py`
- Test: `tests/` (see test scenarios — new tests needed)

**Approach:**
- On `PlayerInGame`: remove `pop_action`, `queue_action`, `clear_queued_actions` abstract methods; add `next_action() -> ActionRequest` as the single abstract method
- On `Human`: replace `pop_action()` with `next_action()` returning `ConcreteAction(self.queued_actions.popleft())` or `NoAction()`; change `deque.pop()` to `deque.popleft()` (FIFO fix); `queue_action` and `clear_queued_actions` remain as concrete methods, no longer declared on base
- On `NaiveCpu`: replace `pop_action()` returning `None` with `next_action()` returning `RequestAutomation()`; remove `queue_action` and `clear_queued_actions` entirely (no raises needed — callers are guarded at the `Game` layer)
- Delete the `TODO` comment on the old `NaiveCpu.pop_action()`

**Execution note:** Implement `next_action()` test-first — write the player unit tests before the implementation so the FIFO fix and the `RequestAutomation` return are each red-then-green.

**Patterns to follow:**
- `Human.queue_action()` / `Human.clear_queued_actions()` style (return `Self`, mutate deque) — unchanged
- `@abstractmethod` convention in `PlayerInGame`

**Test scenarios:**
- Happy path: `Human` with one queued action — `next_action()` returns `ConcreteAction` wrapping that action and removes it from the deque
- Happy path: `Human` with empty queue — `next_action()` returns `NoAction()`
- Happy path: FIFO ordering — `Human` queues action A then action B; first `next_action()` returns `ConcreteAction(A)`, second returns `ConcreteAction(B)` (not reversed)
- Happy path: `NaiveCpu.next_action()` returns `RequestAutomation()` instance
- Edge case: `Human` queue with multiple actions — calling `next_action()` N times consumes exactly N actions in insertion order, then returns `NoAction()`
- Edge case: `Human.queue_action()` and `Human.clear_queued_actions()` still exist and work correctly on `Human` instances
- Error path: confirm `Human.queue_action()` / `clear_queued_actions()` are NOT accessible via `PlayerInGame` typed reference (i.e., static type checker error, verified by pyright)

**Verification:**
- `pyright` passes with no new errors
- All new player unit tests pass
- `pytest tests/` passes (no existing tests regressed)

---

- [ ] **Unit 3: Update `Game.__automated_act()`, `queue_action_for()`, and `clear_queued_actions_for()`**

**Goal:** Rewrite `__automated_act()` to dispatch on `ActionRequest`; add WON-state guard; add type-narrowing guards to the two queue methods.

**Requirements:** R8, R9, R10

**Dependencies:** Unit 2

**Files:**
- Modify: `src/models/internal/game.py`
- Test: `tests/` (see test scenarios — new integration tests needed)

**Approach:**
- `__automated_act()`: replace the `while pop_action() is not None` walrus with a `while True` loop; **the `if self._engine.winner: break` guard must be the first statement inside the loop body, before any access to `self.active_player_id`** (which raises `StopIteration` on a won engine); then resolve the active player, call `player.next_action()` and dispatch with `match`; on `NoAction` → break; on `ConcreteAction(action)` → existing valid/invalid logic, **but** the `clear_queued_actions()` call must be on a type-narrowed `Human` reference (the player at that site is always a `Human` by invariant — use `assert isinstance(active_player, Human)` or an `isinstance` guard) followed by `break`; on `RequestAutomation` → call `naive_action_for(self._engine, active_player_id)`, wrap result with `ActionFactory.from_engine()`, call `engine.act()`, and continue the loop
- `queue_action_for()`: add `isinstance(player, Human)` check before calling `player.queue_action(action)`; if not `Human`, raise `BadRequestError` (preserves existing HTTP 400 behavior for CPU player attempts)
- `clear_queued_actions_for()`: same `isinstance(player, Human)` guard before calling `player.clear_queued_actions()`

**Patterns to follow:**
- `match` / `case` dispatch in `src/mappers/db/serialize.py` (lines 58–63) — use same pattern for `ActionRequest` variants
- `BadRequestError` raised at the model layer — consistent with prior `NaiveCpu.queue_action()` behavior
- `naive_action_for(self._engine, player_id)` pattern from `suggestion_for()` (game.py line 281)
- `ActionFactory.from_engine(...)` to convert automation result to internal action

**Test scenarios:**

*`__automated_act` — CPU automation:*
- Happy path: after a human acts, the next active player is `NaiveCpu` — `__automated_act()` calls `naive_action_for`, the CPU acts, loop terminates when it's a `Human`'s turn with no queued actions
- Happy path: two consecutive `NaiveCpu` players — both act in sequence within a single `__automated_act()` invocation
- Edge case: game reaches WON state during CPU chain — `__automated_act()` exits cleanly without raising `StopIteration` or any other exception
- Integration: `game.queue_action_for(human_player_id, valid_action)` where the queued action is immediately playable triggers `__automated_act()`; any following CPU turns chain to completion; game state stabilizes at next human turn
- Integration: `game.act(human_action)` followed by CPU turns resolves to a stable game state persisted correctly (no action-log / engine state mismatch)

*`__automated_act` — Human queue (regression):*
- Happy path: human has one valid queued action — it is consumed and engine advances
- Edge case: human has an invalid queued action — queue is flushed, loop exits, no further actions taken
- Edge case: human has multiple queued actions where the first is valid and the second is invalid — first plays, second triggers flush

*`queue_action_for` / `clear_queued_actions_for` type-narrowing:*
- Error path: calling `game.queue_action_for(naive_cpu_player_id, action)` raises `BadRequestError` — HTTP layer returns 400 (regression test for `test_only_human_players_queue`)
- Error path: calling `game.clear_queued_actions_for(naive_cpu_player_id)` raises `BadRequestError` — HTTP layer returns 400 (regression test for `test_only_human_players_clear_queue`)
- Happy path: `queue_action_for` for a `Human` player still works correctly

**Verification:**
- `pytest tests/` passes including `test_only_human_players_queue` and `test_only_human_players_clear_queue`
- A full game with CPU players can be played to completion via `act()` without exceptions
- `pyright` passes on `game.py`

---

- [ ] **Unit 4: Update `UnknownPerson` test stub and audit test helpers**

**Goal:** Update the one test-file `PlayerInGame` stub to implement `next_action()` instead of the three removed methods; audit test helpers for patterns flagged in institutional learnings.

**Requirements:** R1, R2 (test compatibility)

**Dependencies:** Unit 2

**Files:**
- Modify: `tests/mappers/test_mapper_edge_cases.py`
- Review (no change expected): `tests/helpers.py`

**Approach:**
- `UnknownPerson(PlayerInGame)` in `test_mapper_edge_cases.py` implements `pop_action`, `queue_action`, `clear_queued_actions` as the three abstract methods. Replace with a single `next_action()` implementation returning `NoAction()`. Add `NoAction` to the imports from `src.models.internal` in that file (it is not currently imported there).
- Audit `tests/helpers.py` for: bare `contains_unsequenced()` calls without `assert`, `[:-1]` slices, and hardcoded `DEFAULT_ID` constants inside helpers that take `player_id` as a parameter. Fix any found. Note: the current file already has no bare `contains_unsequenced()` calls; the audit is to confirm this and check for any similar patterns introduced during this refactor.
- Add return type annotations to any `helpers.py` functions missing them (flagged in learnings doc)

**Patterns to follow:**
- `docs/solutions/test-failures/silent-assert-and-wrong-slice-in-test-helpers-2026-04-09.md` — checklist for helper audit
- `docs/solutions/logic-errors/queue-action-hardcoded-player-id-assertion-2026-04-09.md` — constant-vs-parameter audit

**Test scenarios:**
- Happy path: `test_mapper_edge_cases.py` tests pass unchanged after `UnknownPerson` is updated
- Verification: add one deliberate counter-example assertion in the test for any fixed helper — confirm it can fail

**Verification:**
- `pytest tests/mappers/test_mapper_edge_cases.py` passes
- `pylint` / `ruff` passes on `tests/helpers.py` with no `W0104` (pointless-statement) warnings
- `pyright` passes on `tests/` with no new errors

## System-Wide Impact

- **Interaction graph:** `Game.__automated_act()` is the only code path that calls player action methods. It is triggered by `game.act()` and `game.queue_action_for()`, both called from `src/routers/games.py`. No middleware, observers, or callbacks are affected.
- **Error propagation:** `BadRequestError` raised in `Game.queue_action_for()` / `clear_queued_actions_for()` propagates to `src/routers/games.py` via the existing `game_exception_handler` middleware — same HTTP 400 behavior as before.
- **State lifecycle risks:** The WON-state guard prevents the engine from being called after game completion. The `RequestAutomation` branch advances the engine directly via `engine.act()` without calling `_update_game_player` — CPU turns do not modify player objects, so no player update is needed and no engine re-initialization occurs mid-chain. Engine re-initialization only happens on the invalid-action flush path (`_update_game_player(player.clear_queued_actions())`). Because `self.actions` is derived from the engine's action log, the engine and action list stay in sync across the entire chain.
- **API surface parity:** `src/mappers/client/serialize.py` already guards with `isinstance(player_in_game, internal.Human)` before accessing `queued_actions` — no change needed. `src/mappers/db/serialize.py` accesses `person.queued_actions` as a field directly on `Human` — no change needed.
- **Integration coverage:** A test simulating a full game where a human takes a single action and CPU players complete all remaining turns (to WON state) is the critical cross-layer scenario that unit tests alone will not prove. This must be an end-to-end test via `game.act()`.
- **Unchanged invariants:** The `suggestion_for()` method, all HTTP routes, the MongoDB schema, and client response models are unchanged. The `Action` type and its `to_engine()` / `from_engine()` converters are unchanged.

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| `naive_action_for` contract undefined — could return an action for a wrong player or in a degenerate state | WON-state guard prevents calling it on a completed game. Contract already used in `suggestion_for()` with no issues. |
| CPU automation chain could play many turns in one synchronous call (full game from one `act()`) | Intentional; architecture has no async turn-taking. Only a performance concern for very long games — acceptable for current scope. |
| FIFO fix (popleft) changes existing queue behavior | Test coverage with multiple-action queues explicitly validates ordering. `test_queue_multiple_actions` will catch regressions. |
| `UnknownPerson` stub update could silently break if the test also asserts player method behavior | The test only exercises serializer error handling (unknown type → `ValueError`) — the stub's action behavior is irrelevant to that test. |
| Missing `assert` in test helpers (re: learnings) re-introduced during helper updates | Unit 4 includes an explicit helper audit against the two learnings docs. |

## Sources & References

- **Origin document:** [`docs/brainstorms/player-automation-api-requirements.md`](docs/brainstorms/player-automation-api-requirements.md)
- Related code: `src/models/internal/player.py`, `src/models/internal/game.py`, `src/models/internal/actions.py`
- Related code: `tests/mappers/test_mapper_edge_cases.py`, `tests/helpers.py`
- Institutional learnings: `docs/solutions/test-failures/silent-assert-and-wrong-slice-in-test-helpers-2026-04-09.md`
- Institutional learnings: `docs/solutions/logic-errors/queue-action-hardcoded-player-id-assertion-2026-04-09.md`
