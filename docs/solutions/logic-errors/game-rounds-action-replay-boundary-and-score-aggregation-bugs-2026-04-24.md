---
title: "Game.rounds action-replay: game-ending boundary off-by-one and lossy score aggregation"
date: 2026-04-24
last_updated: 2026-04-24
category: logic-errors
module: src/models/internal/game.py
problem_type: logic_error
component: service_object
severity: high
symptoms:
  - "Final round of a completed game appears truncated or shows wrong trick count in Game.rounds"
  - "Per-round score totals are wrong when a player wins multiple tricks — values reflect only the last score entry, not the sum"
  - "Coverage tool reports a missed branch (e.g., 338->342) for a match/case arm that is fully exercised in tests"
root_cause: logic_error
resolution_type: code_fix
related_components:
  - src/models/internal/round.py
  - src/models/internal/game.py
tags:
  - action-replay
  - round-boundary
  - off-by-one
  - score-aggregation
  - match-case
  - coverage-pragma
  - python-3-14
  - game-engine
---

# Game.rounds action-replay: game-ending boundary off-by-one and lossy score aggregation

## Problem

Action-walking replay in `Game.rounds` incorrectly assumed the completed round is always at `rounds[-2]` when a round boundary is detected, causing the wrong round to be read for the game-winning action. A related pre-existing bug in `Game.events` builds per-round score dicts with a comprehension that silently overwrites duplicate player entries, producing wrong totals whenever a player scores across multiple tricks in a round.

## Symptoms

- `Game.rounds` returns a round with fewer than the expected number of tricks for the final round of a completed game (the last round appears truncated).
- Sum of per-round score deltas does not equal the game's cumulative `scores` — individual player totals are lower than expected when they win multiple tricks in one round.
- Coverage tool reports a missed branch (`N->M`) for a `case Play(): pass` arm in structural pattern matching, even when Play actions are fully exercised.

## What Didn't Work

- **Unconditional `rounds[-2]`** for the completed round when a boundary is detected: this holds for every mid-game round transition but silently fails for the game-winning action because the engine does not start a new round after the last play, leaving `rounds[-2]` pointing at the second-to-last round instead of the just-completed one. (session history: this code passed two separate code reviews in earlier sessions on the replay implementation PR without the off-by-one being caught.)
- **Dict comprehension for score aggregation**: `{s.identifier: s.value for s in round.scores}` was written under the assumption that `round.scores` is a keyed mapping. It is a list with one entry per trick won plus bid penalties — multiple entries per player are expected. The comprehension keeps the last value per player and silently discards earlier ones.
- **`# pragma: no cover` on the entire match arm**: annotating the `case Play():` line hides the arm body from coverage, which is worse than the false-positive — real coverage gaps in the arm's neighbors become invisible. The artifact is on the implicit fall-through branch from the `pass` body, not the arm itself.

## Solution

**Primary fix — game-winning boundary detection (`src/models/internal/game.py`)**

The condition `after_round_count > before_round_count` distinguishes mid-game transitions (new round opened) from the game-winning action (round finalized, no new round):

```python
# Before — always reads the penultimate round
completed_engine_round = replay_engine.rounds[-2]

# After — selects the correct round based on whether a new one was started
if after_round_count > before_round_count:
    # Mid-game: new round was opened, completed round is at [-2]
    completed_engine_round = replay_engine.rounds[-2]
else:
    # Game-winning: no new round started, completed round is at [-1]
    completed_engine_round = replay_engine.rounds[-1]
```

Empirical verification: for the game-winning action `before_round_count == after_round_count`, and `replay_engine.rounds[-1]` contains the expected 5 complete tricks.

**Related fix — lossy score aggregation**

The engine's `round.scores` is a list of `Score(identifier, value)` objects — one entry per trick won and one per bid penalty — with multiple entries per player per round:

```python
# Before — overwrites duplicate entries, last one wins
scores={s.identifier: s.value for s in completed_engine_round.scores}

# After — sums all entries per player
score_totals: dict[str, int] = {}
for score_entry in completed_engine_round.scores:
    score_totals[score_entry.identifier] = (
        score_totals.get(score_entry.identifier, 0) + score_entry.value
    )
```

Verification: sum of all per-round `score_totals` now equals `game.scores` (cumulative) across all rounds.

**Coverage artifact — Python 3.14 structural pattern matching**

Mark only the specific line or condition generating the artifact, not the whole arm or block.

Unreachable guard in a `match` arm body:
```python
case SelectTrump():
    current_round.trump = action.suit
    if current_round.bidder is None:
        current_round.bidder = action.player_id  # pragma: no cover
```

Spurious missed-branch on a condition that is always True in practice:
```python
for engine_trick in replay_engine.active_round.tricks:
    if engine_trick.plays:  # pragma: no branch — engine never yields empty-plays tricks here
        current_round.tricks.append(...)
```

## Why This Works

The engine's round list only grows when a new round actually begins. For a mid-game round boundary, `engine.act()` on the last trick finalizes the round and immediately starts the next — `len(rounds)` increments and the just-completed round sits at `rounds[-2]`. The game-winning action is different: the engine finalizes the round and the game ends without initializing a successor, so `len(rounds)` does not change and `rounds[-1]` is the completed round.

The engine models scoring as a list of independent ledger entries (one per trick won, one per bid penalty), deliberately allowing multiple entries per player per round. A dict comprehension is destructive over this list; explicit `dict.get(..., 0)` accumulation sums all entries correctly.

## Prevention

- **Test the terminal game state explicitly.** Any replay-based property (`events`, `rounds`) must have an integration test that runs a full game to completion and asserts properties of the final round, not just mid-game transitions.

  ```python
  def test_completed_game_scores_sum_to_cumulative() -> None:
      g = _make_completed_game()
      round_sum: dict[str, int] = {}
      for round_ in g.rounds:
          if round_.scores:
              for player_id, value in round_.scores.items():
                  round_sum[player_id] = round_sum.get(player_id, 0) + value
      assert round_sum == g.scores
  ```

- **Verify the index separately for mid-game and game-over transitions.** The same replay code path cannot use `[-2]` unconditionally — mid-game transitions open a new round (`rounds[-2]` is correct) but the game-winning action does not (`rounds[-1]` is correct). Test both cases explicitly.

- **Never use a dict comprehension to aggregate a multi-entry ledger.** When the engine exposes a list of score entries, treat it as a ledger with explicit accumulation:

  ```python
  # Correct — sums all entries per player
  totals = {}
  for entry in round.scores:
      totals[entry.identifier] = totals.get(entry.identifier, 0) + entry.value

  # Wrong — silently clobbers duplicate entries
  totals = {entry.identifier: entry.value for entry in round.scores}
  ```

- **Annotate coverage pragmas narrowly.** Use `# pragma: no cover` only on the specific line that is genuinely unreachable, and `# pragma: no branch` only on the specific condition where one branch is structurally impossible. Never annotate an entire arm or block — this hides real gaps in neighboring lines.

## Related Issues

- [`docs/solutions/logic-errors/round-start-hands-lost-to-in-place-mutation-2026-04-11.md`](round-start-hands-lost-to-in-place-mutation-2026-04-11.md) — the prior action-walking replay doc. **Note:** that doc states "the completed round is at `engine.rounds[-2]`" as a general rule. This is correct for mid-game transitions but not for the game-winning action; see the primary fix above for the correct conditional pattern.
- `src/models/internal/game.py:270-274` — `Game.events` contains the same lossy dict comprehension for `RoundEnd.scores`; that path is a pre-existing bug that should be addressed in the same codebase pass.

> **Superseded for `Game.rounds`**: The action-walking replay described in this doc has been replaced for `Game.rounds` by direct engine round inspection with `EngineRound` reconstruction for initial hands. See [`docs/solutions/best-practices/engine-round-reconstruction-for-initial-hands-2026-04-24.md`](../best-practices/engine-round-reconstruction-for-initial-hands-2026-04-24.md). The bugs documented here (`rounds[-2]`/`[-1]` boundary, lossy scores) no longer apply to `Game.rounds`; `Game.events` still uses the action-walking replay and is still subject to the score aggregation bug.
