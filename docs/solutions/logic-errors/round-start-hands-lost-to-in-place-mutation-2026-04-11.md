---
title: "RoundStart hands lost to in-place engine mutation during discard"
date: 2026-04-11
category: logic-errors
module: event-derivation
problem_type: logic_error
component: service_object
severity: high
symptoms:
  - "RoundStart events carried post-discard hands instead of originally dealt hands"
  - "Structural inspection of finished rounds could not recover original dealt hands after engine mutation"
  - "Client hand-visibility filtering had no dealt-hand snapshot to work from"
root_cause: logic_error
resolution_type: code_fix
related_components:
  - tooling
tags:
  - event-derivation
  - action-walking
  - replay
  - round-start
  - hand-mutation
  - engine
  - state-transitions
  - visibility-filtering
---

# RoundStart hands lost to in-place engine mutation during discard

## Problem

`Game.events` derived `RoundStart` events by structurally inspecting finished engine rounds, but the engine mutates `RoundPlayer.hand` in-place during discards. By the time a round is "finished" and inspectable, the originally dealt hands are gone — overwritten. Clients receiving `ROUND_START` events saw post-discard hands, which broke hand-visibility filtering (the serializer couldn't distinguish "this player's cards" from "count of other players' cards").

## Symptoms

- `RoundStart.hands` contained the post-discard hand, not the originally dealt hand
- Replaying a completed game's event log showed wrong hand sizes for other players at round start
- Hand-visibility filtering in the serializer silently produced incorrect results: `len(hand)` mismatched actual dealt count

## What Didn't Work

- **`__round_events` + `__original_hand` via `DetailedDiscard.kept`**: An earlier approach tried to reconstruct dealt hands by inverting the discard — take the kept cards from `DetailedDiscard.kept` and reconstruct the full hand. This was fragile: `DetailedDiscard` was removed in the engine v2 API, and the reconstruction only worked if you could trust the discard record, which was itself stored post-mutation.
- **Inspecting `engine.rounds[-1]` after the round completes**: The completed round's `players[*].hand` reflects the end state, not the dealt state. There is no snapshot of the original hand on a finished round.

## Solution

Replace structural round inspection with an **action-walking replay**. Construct a fresh `Engine` using plain `EnginePlayer` instances (not `Human`/`NaiveCpu`) and the game's seed. The critical change: snapshot hands *immediately* after engine construction, before any actions are replayed.

```python
# Before — hands read after round completes (already mutated by discards)
completed_round = engine.rounds[-1]
RoundStart(hands={p.identifier: p.hand for p in completed_round.players})

# After — hands read immediately after fresh engine construction (pre-mutation)
engine = Engine(
    players=[EnginePlayer(p.id) for p in self.ordered_players],
    seed=self.seed,
)
RoundStart(
    dealer=engine.active_round.dealer.identifier,
    hands={
        p.identifier: [Card.from_engine(c) for c in p.hand]
        for p in engine.active_round.players
    },
)
```

Then replay each stored action one at a time, detecting round and trick boundaries by comparing `len(engine.rounds)` and `len(engine.active_round.tricks)` before and after each `engine.act()` call. At each mid-game round boundary, the completed round is at `engine.rounds[-2]` (the new active round is `[-1]`), and hands for the new `RoundStart` are again snapshotted from the fresh active round before any actions in that round are applied.

**Caveat — game-winning action:** When the game-winning action completes a round, the engine does not start a new round. `len(engine.rounds)` does not increase, so `rounds[-2]` is the second-to-last round (wrong). Use `rounds[-1]` when `replay_engine.winner is not None` and no new round was opened. See [`docs/solutions/logic-errors/game-rounds-action-replay-boundary-and-score-aggregation-bugs-2026-04-24.md`](game-rounds-action-replay-boundary-and-score-aggregation-bugs-2026-04-24.md) for the complete fix pattern.

See `src/models/internal/game.py:204` for the full implementation.

Two related fixes were applied alongside this change:

**`Discard.cards` must be `tuple[Card, ...]`, not `list[Card]`** — `Discard` is a `@dataclass(frozen=True)`. A frozen dataclass instance is only hashable if all its field values are hashable — this matters when `Discard` instances need to be placed in sets or used as dict keys (e.g. the engine's available-action comparison). `list` is unhashable; `tuple` satisfies the constraint.

```python
# Before
cards: list[Card]          # unhashable — breaks hashing of the frozen dataclass

# After
cards: tuple[Card, ...]    # hashable — correct when the instance needs to be hashed
```

**`RoundStart.hands` must not have a mutable default** — both the internal `actions.RoundStart` (a frozen dataclass) and the client `responses.RoundStart` (a Pydantic `BaseModel`) previously declared `hands: dict[...] = {}` or `hands: dict[...] = field(default_factory=dict)`. Neither field needs a default because `RoundStart` is always constructed with an explicit `hands=` argument. Removing the default avoids Python's shared-mutable-default hazard and removes a spurious Pydantic validation warning.

```python
# Before (actions.py — dataclass)
hands: dict[str, list[Card]] = field(default_factory=dict)

# After
hands: dict[str, list[Card]]

# Before (responses.py — Pydantic)
hands: dict[str, Union[list[Card], int]] = {}

# After
hands: dict[str, Union[list[Card], int]]
```

## Why This Works

The state-transition detection works because the engine tracks completed rounds cumulatively in `engine.rounds`. When `len(engine.rounds)` increases after an `engine.act()` call, the round that just completed is at index `[-2]` (the new active round is `[-1]`). Trick boundaries use the same logic within the active round. **Exception:** when the game-winning action completes, `len(engine.rounds)` does not increase — the completed round is at `[-1]`, not `[-2]`. See the caveat in the Solution section above.

Using plain `EnginePlayer` (not `Human` or `NaiveCpu`) keeps the replay passive — the engine does not attempt to automate any actions during the walk.

### Ghost-round false alarm

During review, it looked like a completed game might produce a spurious extra `RoundStart` event: `_update_game_player` calls `__initialize_engine`, which calls `__automated_act`, which loops while `not self.winner`. The concern was that `self.winner` might be falsy even after a game-winning play, causing the loop to continue and trigger a new round.

Investigation confirmed this is not a problem: `Game.status` returns `GameStatus.WON` (not `GameStatus.COMPLETED`) when `self._engine.winner` is set. The `__automated_act` guard checks `not self.winner` — once a winner exists, the loop exits. The `events` property uses its own local `engine` instance and checks `engine.winner` directly, so the same is true there.

## Prevention

- **Snapshot engine state eagerly** — if an event model requires state at a moment in time, capture it at that moment, not after subsequent mutations. This applies to dealt hands, trick state, round scores, and any other engine data that changes during play.
- **Use plain `EnginePlayer` for replay** — `Human` and `NaiveCpu` both carry side-effectful behaviour (queued actions, automation). Replay engines should always use the base `EnginePlayer` to stay passive.
- **A `frozen=True` dataclass instance is only hashable when all its fields are hashable** — this matters if the instance needs to go in a `set` or be used as a `dict` key. Use `tuple` instead of `list` and `frozenset` instead of `set` for those fields. Note: `frozen=True` on its own only prevents field *re-assignment*; fields can still hold mutable types (like `dict` or `list`) if the instance itself never needs to be hashed. Linters do not catch the hash requirement; a runtime `TypeError: unhashable type` is the first signal.
- **Test event sequences end-to-end** — add a test that replays a complete multi-round game and asserts the sequence and content of `RoundStart.hands` events against expected dealt hands. This catches both the mutation bug and any future regressions in the replay logic.

```python
def test_round_start_hands_reflect_dealt_cards():
    """RoundStart hands must equal the dealt hand, not the post-discard hand."""
    # make_complete_game() is a hypothetical unit-test fixture that constructs
    # an internal Game instance directly (not via HTTP) and drives it to completion.
    game = make_complete_game()
    events = game.events
    round_starts = [e for e in events if isinstance(e, RoundStart)]
    for rs in round_starts:
        for player_id, hand in rs.hands.items():
            assert len(hand) == 5, (  # 110 deals 5 cards per player
                f"Player {player_id} had {len(hand)} cards at RoundStart"
            )
```

## Related Issues

- [`docs/solutions/best-practices/action-request-discriminated-union-player-automation-2026-04-10.md`](../best-practices/action-request-discriminated-union-player-automation-2026-04-10.md) — the `__initialize_engine` replay loop is the direct ancestor of the action-walking pattern used here; the two docs share the same engine re-construction idiom
- `docs/plans/2026-04-10-002-refactor-event-derivation-replay-plan.md` — plan that drove this refactor (status: completed)

> **Partially superseded for `Game.rounds`**: The action-walking replay described here as the solution is still used for `Game.events`. For `Game.rounds`, it has been replaced by direct engine inspection with targeted `EngineRound` reconstruction for initial hands — a cheaper alternative that avoids a full replay while still recovering pre-discard dealt hands. See [`docs/solutions/best-practices/engine-round-reconstruction-for-initial-hands-2026-04-24.md`](../best-practices/engine-round-reconstruction-for-initial-hands-2026-04-24.md).
