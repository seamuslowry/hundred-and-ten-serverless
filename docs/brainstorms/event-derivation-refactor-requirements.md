---
date: 2026-04-10
topic: event-derivation-refactor
---

# Event Derivation Refactor

## Problem Frame

The game's event timeline (`Game.events`) is currently derived by reading finished
engine state -- `__round_events` walks each round's bids, discards, tricks, etc. after
all actions have already been replayed. This approach cannot reconstruct a player's
originally dealt hand because the engine mutates `RoundPlayer.hand` in-place during
discards. The old v1 engine had `DetailedDiscard` with a `kept` field that made
reconstruction possible, but v2 correctly dropped that -- it conflated derived state
with action input.

The fix is to change how events are derived: instead of reading from finished rounds,
walk the action list and observe state transitions during a separate replay. This
naturally captures intermediate state (like dealt hands before discards) and produces
a cleaner, more explicit event derivation model.

## Chosen Approach

**Action-walking event derivation with a separate replay.**

Event derivation constructs a fresh engine from the game's seed and players, then steps
through each action one at a time. Before and after each action, it checks for state
transitions (new round, new trick, round completion, game completion) and emits the
corresponding derived events. Because the replay is stepped, intermediate state like
dealt hands is available at the natural moment -- right after a round is created, before
any actions mutate it.

This is a separate replay from `__initialize_engine`, which continues to handle current
game state construction. The double replay is acceptable because events are computed
infrequently (client reads, not hot path).

### Why not alternatives

- **Snapshot during `__initialize_engine`**: Couples event derivation to the state
  initialization path. Two separate concerns (current state vs. timeline) would share
  a single replay, making each harder to change independently.
- **Engine exposes `dealt_hands` on `Round`**: Clean but requires an engine release for
  something that the app can derive. The engine's job is rules, not history.
- **Reconstruct from seed + deck math**: Duplicates engine internals (deck seeding,
  deal order). Brittle if the engine's dealing logic ever changes.

## Requirements

**Event derivation algorithm**

- R1. `Game.events` produces the event timeline by constructing a fresh engine from the
  game's seed and player list, then replaying all actions one at a time.
- R2. The replay is independent of `__initialize_engine` -- it does not share state or
  depend on the game's live engine instance.
- R3. Actions are emitted in chronological (action-list) order. This matches the
  current ordering produced by `__round_events`, which reads bids, selection, discards,
  then trick plays -- the same order they were applied.
- R4. Events are derived by detecting state transitions before and after each action:
  - `GameStart`: emitted once at the beginning (before any actions).
  - `RoundStart`: emitted whenever a round first becomes visible during the replay --
    once for the initial round (created at engine construction) and once each time a
    subsequent round is created (which happens automatically after a round completes).
    This includes the active in-progress round. Carries the dealer identifier and the
    dealt hands.
  - Action events (`Bid`, `SelectTrump`, `Discard`, `Play`): emitted for each action
    as it is applied.
  - `TrickStart`: emitted when a new trick appears -- once when the first trick is
    created (after all discards) and once each time a subsequent trick is created
    (after the previous trick completes).
  - `TrickEnd`: emitted when a trick completes (all players have played and a winning
    play exists). Carries the winning player's identifier.
  - `RoundEnd`: emitted when a round completes. Carries the round's scores.
  - `GameEnd`: emitted after all actions are applied if the game has a winner.
- R5. The `events` property is reimplemented per R1-R4. The existing `__round_events`
  static method and the commented-out `__original_hand` method are removed.

**`RoundStart` event: dealt hands**

- R6. The internal `RoundStart` event (in `src/models/internal/actions.py`) carries a
  `hands` field: `dict[str, list[Card]]` mapping player identifiers to their dealt
  hands.
- R7. The client-facing `RoundStart` response (in `src/models/client/responses.py`)
  carries a `hands` field: `dict[str, list[Card] | int]`. For the requesting player,
  the value is the full list of cards. For all other players, the value is the card
  count (integer).
- R8. The client serializer maps between the internal and client representations,
  applying the visibility rule from R7 based on the requesting player's identity.

**Cleanup**

- R9. All commented-out code related to `__original_hand`, `hands` on `RoundStart`,
  and the old client serialization of hands is either replaced by working
  implementations or removed entirely. No dead comments should remain.

## Non-Goals

- Modifying the `hundredandten-engine` package. All changes are in this serverless app.
- Changing the DB persistence format. Actions (moves) are stored the same way.
- Exposing opponent hand contents. Opponents see card counts only.
- Optimizing the double replay. Correctness and separation of concerns come first.

## Success Criteria

- `Game.events` returns the same action events and derived events as before, plus
  `RoundStart.hands` is populated with each player's originally dealt cards.
- The event derivation replay constructs its own engine instance and does not read
  from or write to `self._engine`.
- The client response for a game's events includes dealt hands on `RoundStart` with
  proper visibility (own cards vs. opponent counts).
- No commented-out code remains for the old `__original_hand` or `hands` fields.
- Existing tests pass. New tests cover the event derivation logic, including multi-round
  games where dealt hands differ per round.
