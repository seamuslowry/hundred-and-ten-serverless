---
title: "refactor: Replace structural-inspection event derivation with action-walking replay"
type: refactor
status: active
date: 2026-04-10
origin: docs/brainstorms/event-derivation-refactor-requirements.md
---

# refactor: Replace structural-inspection event derivation with action-walking replay

## Overview

Replace the current `Game.events` implementation — which derives events by inspecting
finished engine rounds — with an action-walking replay that steps through stored actions
one at a time and emits events by observing state transitions. This enables capturing
intermediate state like originally dealt hands, which are lost in the current approach
because the engine mutates player hands in-place during discards.

## Problem Frame

The engine's `RoundPlayer.hand` is mutated during discards (remaining cards kept, new
cards drawn from deck). By the time `__round_events` inspects a finished round, the
original dealt hands are gone. The old v1 engine had `DetailedDiscard.kept` to
reconstruct them, but v2 correctly dropped that. The action-walking approach captures
dealt hands at the natural moment — right after a round is created, before any actions
mutate it. (see origin: `docs/brainstorms/event-derivation-refactor-requirements.md`)

## Requirements Trace

- R1. Event timeline produced by constructing a fresh engine and replaying actions
- R2. Replay is independent of `__initialize_engine` (separate engine instance)
- R3. Actions emitted in chronological order (matches current ordering)
- R4. Events derived by detecting state transitions (round/trick creation, completion)
- R5. `events` property reimplemented; `__round_events` and `__original_hand` removed
- R6. Internal `RoundStart` carries `hands: dict[str, list[Card]]`
- R7. Client `RoundStart` carries `hands: dict[str, list[Card] | int]` with visibility
- R8. Client serializer applies visibility rule (own cards vs. opponent counts)
- R9. All commented-out code for hands/original_hand removed or replaced

## Scope Boundaries

- No changes to the `hundredandten-engine` package
- No changes to DB persistence format (actions/moves stored the same way)
- No changes to the `__initialize_engine` replay path
- No optimization of double replay — correctness and separation first
- Opponent hand contents never exposed (card counts only)

## Context & Research

### Relevant Code and Patterns

- `src/models/internal/game.py:208-216` — Current `events` property using `__round_events`
- `src/models/internal/game.py:301-348` — `__round_events` + commented-out `__original_hand`
- `src/models/internal/game.py:350-359` — `__initialize_engine` pattern to mirror
- `src/models/internal/actions.py:156-161` — `RoundStart` with commented-out `hands`
- `src/mappers/client/serialize.py:171-255` — `__event` with commented-out hands mapping
- `src/mappers/client/serialize.py:208-217` — `Discard` visibility rule (analogous pattern)
- `src/models/client/responses.py:70-75` — Client `RoundStart` with commented-out `hands`
- `.venv/.../hundredandten/engine/game.py` — Engine `Game` class
- `.venv/.../hundredandten/engine/round.py` — Engine `Round` class, hand mutation at line 349

### Institutional Learnings

- `docs/solutions/best-practices/action-request-discriminated-union-player-automation-2026-04-10.md`:
  Use `Engine(players=[EnginePlayer(p.id) for p in self.ordered_players], seed=self.seed)`
  for engine construction. The event replay must NOT call `__automated_act()` or touch
  `self._engine`.
- `docs/solutions/test-failures/silent-assert-and-wrong-slice-in-test-helpers-2026-04-09.md`:
  Always `assert` predicate helpers like `contains_unsequenced()`. Watch slice directions.
- `docs/solutions/logic-errors/queue-action-hardcoded-player-id-assertion-2026-04-09.md`:
  Use parameterized player IDs in assertions, test with multiple distinct players.

## Key Technical Decisions

- **Separate replay engine**: The event derivation constructs its own `Engine` instance
  using `EnginePlayer` (not `Human`/`NaiveCpu`). This means no automated actions fire
  during event replay — only explicitly stored actions are replayed. This avoids the
  cascade concern entirely.

- **State transition detection via counts**: Before and after each `engine.act()`, track
  `len(engine.rounds)` and `len(engine.active_round.tricks)` to detect round and trick
  boundaries. This handles the engine's auto-creation of rounds and tricks inside `act()`.

- **`COMPLETED_NO_BIDDERS` detection**: When all players pass, the engine creates a new
  round inside `act()`. The event replay detects this via round count change. The old
  completed round is `engine.rounds[-2]`. Its `completed` flag is `True` and its scores
  (all zeros) are emitted in `RoundEnd`, matching current behavior.

- **Dealt hand snapshot timing**: Hands are captured from `engine.active_round.players`
  immediately after the engine is constructed (first round) and immediately after
  detecting a round count increase (subsequent rounds). At both moments, hands are
  pristine — no actions have mutated them yet.

- **No new event types**: `RoundEnd` for no-bidder rounds continues to carry zero scores.
  This matches current behavior and avoids a breaking client change.

## Open Questions

### Resolved During Planning

- **How to detect round boundaries**: Round count comparison before/after each action.
  Engine auto-creates rounds inside `act()`, so `len(engine.rounds)` is sufficient.
- **How to detect trick boundaries**: Trick count comparison on the active round
  before/after each action. The engine creates tricks inside `Round.__end_discard()`
  (first trick) and `Round.__end_play()` (subsequent tricks).
- **What about the automated action cascade**: Not a concern. The event replay engine
  uses plain `EnginePlayer` instances, not `Human`/`NaiveCpu`. No automation loop runs.
  All actions — including those originally from CPU players — are in the stored action
  list and are replayed explicitly.

### Deferred to Implementation

- **Exact structure of the replay loop**: Whether to use a generator, a builder, or a
  simple list accumulator is an implementation choice.
- **Whether `__round_events` import of `EngineRound` can be removed**: Depends on whether
  any other code references it. The implementer should check.

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review,
> not implementation specification. The implementing agent should treat it as context,
> not code to reproduce.*

```
def events(self) -> list[Event]:
    engine = Engine(players=[...], seed=self.seed)
    events = [GameStart()]

    # Capture first round's dealt hands
    events.append(RoundStart(dealer=..., hands=snapshot_hands(engine)))

    prev_round_count = len(engine.rounds)
    prev_trick_count = len(engine.active_round.tricks)

    for action in self.actions:
        engine.act(action.to_engine())
        events.append(ActionFactory.from_engine(action))

        curr_round_count = len(engine.rounds)
        curr_trick_count = len(engine.active_round.tricks)

        # Detect trick boundary (within same round)
        if curr_round_count == prev_round_count:
            if curr_trick_count > prev_trick_count:
                # Previous trick completed, new trick started
                events.append(TrickEnd(winner=...))
                events.append(TrickStart())

        # Detect round boundary
        if curr_round_count > prev_round_count:
            # Previous round completed (might include final trick end)
            # ... emit TrickEnd if applicable
            # ... emit RoundEnd with scores from completed round
            events.append(RoundEnd(scores=...))
            events.append(RoundStart(dealer=..., hands=snapshot_hands(engine)))

        prev_round_count = curr_round_count
        prev_trick_count = curr_trick_count

    # Game end
    if engine.winner:
        events.append(GameEnd(winner=engine.winner.identifier))

    return events
```

Key insight: the action event is emitted *before* checking for transitions, because the
action caused the transition. The derived events (TrickEnd, RoundEnd, etc.) follow the
action that triggered them.

**Ordering concern for trick-completing plays that also complete a round:**
When the last play in the final trick is applied, `act()` completes the trick AND the
round AND potentially creates a new round — all atomically. The detection logic must
emit events in the right order: `Play → TrickEnd → RoundEnd → RoundStart`.

This is handled because the trick-boundary check is guarded by
`curr_round_count == prev_round_count`, so it is naturally skipped when a round boundary
occurs. The round-boundary block handles the final trick's `TrickEnd` itself — it reads
the last trick of the completed round (`engine.rounds[-2]`) and emits `TrickEnd` before
`RoundEnd`.

## Implementation Units

- [ ] **Unit 1: Add `hands` field to internal and client `RoundStart`**

**Goal:** Un-comment and activate the `hands` field on both the internal and client
`RoundStart` event types.

**Requirements:** R6, R7

**Dependencies:** None

**Files:**
- Modify: `src/models/internal/actions.py`
- Modify: `src/models/client/responses.py`
- Test: `tests/functions/test_game_events.py`

**Approach:**
- Internal `RoundStart`: replace the commented-out `# hands: dict[str, list[Card]]`
  with an active field. Use `default_factory=dict` so existing construction sites
  (`RoundStart(dealer)` in `__round_events`) continue to work until Unit 3 replaces
  them. Since this is a frozen dataclass, add it as a keyword-only field with a default.
- Client `RoundStart`: replace the commented-out `# hands: dict[str, Union[list[Card], int]]`
  with an active Pydantic field, defaulting to an empty dict.
- The internal `RoundStart` currently has only `dealer: str`. After this change it will
  have `dealer: str` and `hands: dict[str, list[Card]]` (defaulting to `{}`).
- The `Game.events` property and serializer will be updated in later units. This unit
  only changes the data models. The default value ensures existing call sites are
  unaffected.

**Patterns to follow:**
- Frozen dataclass pattern matching existing action types in `src/models/internal/actions.py`
- Pydantic model pattern matching existing response types in `src/models/client/responses.py`
- `Discard` visibility pattern in `src/models/client/responses.py:50-56` where `cards`
  is `Union[list[Card], int]`

**Test scenarios:**
- Test expectation: none -- model-only change, tested through integration in Units 3-4

**Verification:**
- `RoundStart` accepts a `hands` dict at construction time
- Client `RoundStart` Pydantic model validates with both list and int values for hands

---

- [ ] **Unit 2: Update client serializer for `RoundStart.hands`**

**Goal:** Activate the commented-out hands mapping in the client serializer, applying
the visibility rule: requesting player sees their cards, opponents see card count.

**Requirements:** R8

**Dependencies:** Unit 1

**Files:**
- Modify: `src/mappers/client/serialize.py`
- Test: `tests/functions/test_game_events.py`

**Approach:**
- In `__event()` for `RoundStart`, replace the commented-out `hands` mapping with active
  code that applies the same visibility pattern as `Discard`: if `player_id == client_player_id`,
  show `[__card(c) for c in hand]`, otherwise show `len(hand)`.
- The mapping iterates `event.hands.items()` and applies the conditional per player.

**Patterns to follow:**
- `Discard` visibility in `src/mappers/client/serialize.py:208-217` — analogous pattern
  of `client_player_id == event.player_id` conditional, adapted as a per-entry dict
  comprehension since `RoundStart.hands` has multiple players rather than one

**Test scenarios:**
- Test expectation: none -- serializer change, tested through integration in Units 3-4

**Verification:**
- Serializer produces client `RoundStart` with `hands` dict populated
- Own player's hand is a list of card objects
- Other players' hands are integer counts

---

- [ ] **Unit 3: Rewrite `Game.events` with action-walking replay**

**Goal:** Replace `__round_events` with an action-walking event derivation method that
steps through actions one at a time, detects state transitions, and emits events
including `RoundStart` with dealt hands.

**Requirements:** R1, R2, R3, R4, R5, R9

**Dependencies:** Units 1, 2

**Files:**
- Modify: `src/models/internal/game.py`
- Test: `tests/functions/test_game_events.py`

**Approach:**
- Replace the `events` property body. The new implementation:
  1. Constructs a fresh `Engine` with `EnginePlayer` instances and `self.seed`
  2. Emits `GameStart`
  3. Snapshots dealt hands from `engine.active_round.players` → emits `RoundStart`
  4. For each action in `self.actions`:
     - Records pre-action state: round count, trick count
     - Calls `engine.act(action.to_engine())`
     - Emits the action event
     - Compares post-action state to detect transitions:
       - Trick count increased (same round): emit `TrickEnd` + `TrickStart`
       - Round count increased: emit `TrickEnd` (for final trick of old round) +
         `RoundEnd` (with scores from completed round) + `RoundStart` (with new dealt
         hands)
  5. After all actions: if `engine.winner`, emit `GameEnd`
- Remove the `__round_events` static method entirely
- Remove the commented-out `__original_hand` method
- Remove the `EngineRound` import if no longer needed

**Execution note:** Run existing event tests first as a characterization baseline to
confirm they pass before making changes. After rewriting, all existing tests must still
pass with the same event sequences.

**Patterns to follow:**
- `__initialize_engine` pattern for engine construction (same players, same seed)
- `ActionFactory.from_engine` for converting engine actions to internal actions

**Test scenarios:**
- Happy path: New game produces `[GameStart, RoundStart(hands=...)]` where `RoundStart`
  has correct dealer and hands dict with all player IDs as keys
- Happy path: Completed game produces the same event types in the same order as before
  the refactor (GameStart → RoundStart → Bids → SelectTrump → Discards → TrickStart →
  Plays → TrickEnd → ... → RoundEnd → ... → GameEnd)
- Edge case: Multi-round game — each `RoundStart` has different dealt hands (different
  deck seeds per round produce different deals)
- Edge case: No-bidder round — all players pass → `RoundEnd(scores={p1: 0, p2: 0, ...})`
  with all player IDs present → `RoundStart` for next round with fresh dealt hands
- Edge case: Game-winning round — final `TrickEnd` → `RoundEnd` → `GameEnd` (no
  `RoundStart` after because game is over)
- Integration: `RoundStart.hands` keys match the player identifiers in the game
- Integration: `RoundStart.hands` values are 5 cards each (HAND_SIZE)
- Integration: Event count and sequence numbers remain consistent with router expectations
  (`len(game.events)` used for slicing in routers)

**Verification:**
- All existing event tests pass without modification
- New tests verify `RoundStart.hands` contains correct dealt hands
- `__round_events` and `__original_hand` no longer exist in the file

---

- [ ] **Unit 4: Verify client-facing `RoundStart.hands` visibility and cleanup**

**Goal:** Verify the full end-to-end flow of dealt hands through to client responses,
and remove all remaining commented-out code.

**Requirements:** R7, R8, R9

**Dependencies:** Units 1, 2, 3

**Files:**
- Modify: `src/models/internal/game.py` (cleanup any remaining comments)
- Modify: `src/mappers/client/serialize.py` (cleanup any remaining comments)
- Modify: `src/models/client/responses.py` (cleanup any remaining comments)
- Test: `tests/functions/test_game_events.py`

**Approach:**
- Write integration tests that verify the client response includes `hands` on
  `RoundStart` with correct visibility rules.
- Audit all three files for any remaining commented-out code related to hands,
  `__original_hand`, or `DetailedDiscard`. Remove it.
- Verify the `Discard` pattern is correctly mirrored: own player sees card list,
  opponents see integer count.

**Patterns to follow:**
- Existing event assertions in `tests/functions/test_game_events.py` using
  `get_events(client, game_id, player_id)`
- `contains_unsequenced` helper for event matching
- Always `assert` predicate helpers (per institutional learning)

**Test scenarios:**
- Happy path: `get_events(client, game_id, own_player_id)` returns `RoundStart` where
  `hands[own_player_id]` is a list of 5 card objects with `suit` and `number` fields
- Happy path: Same `RoundStart` event has `hands[opponent_id]` equal to `5` (integer
  count, not card list)
- Edge case: Game with 2 human players — verify each player's view of the same
  `RoundStart` event shows their own cards and the other player's count (use
  `game_with_manual_player` helper)
- Integration: All event types still serialize correctly (no regression from adding
  `hands` to `RoundStart`)

**Verification:**
- End-to-end tests pass with correct visibility
- No commented-out code remains in any of the three model/serializer files
- Branch coverage does not decrease (CI enforces 100%)

## System-Wide Impact

- **Event slicing in routers:** Routers use `len(game.events)` before mutation and
  `events[initial_event_knowledge:]` after. The new implementation must return a list
  that supports `len()` and slicing. This is preserved — the property still returns
  `list[Event]`.
- **Error propagation:** If the replay engine encounters an invalid action (should never
  happen since actions are stored after successful execution), the error propagates from
  `engine.act()`. This matches current behavior in `__initialize_engine`.
- **Unchanged invariants:** `Game.actions`, `Game.status`, `Game.winner`, `Game.scores`,
  and all other properties continue to read from `self._engine` (the live engine). Only
  `Game.events` changes behavior.

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Event ordering differs subtly from current implementation | Run existing tests as characterization baseline before changes. Compare event sequences in completed-game test. |
| 100% branch coverage requirement with new replay logic | New replay code has clear branch points (round boundary, trick boundary, game end). Each branch is covered by a specific test scenario. |
| `RoundStart.hands` breaks client Pydantic validation | The `hands` field uses `dict[str, Union[list[Card], int]]` which Pydantic handles via discriminated fields. Test serialization round-trip. |

## Sources & References

- **Origin document:** [docs/brainstorms/event-derivation-refactor-requirements.md](docs/brainstorms/event-derivation-refactor-requirements.md)
- Related code: `src/models/internal/game.py` (events property, `__round_events`)
- Engine source: `.venv/.../hundredandten/engine/round.py` (hand mutation at line 349)
- Institutional learnings: `docs/solutions/best-practices/action-request-discriminated-union-player-automation-2026-04-10.md`
