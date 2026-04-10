---
title: "Silent test assertions — bare contains_unsequenced() calls and wrong slice in queue_action()"
date: 2026-04-09
category: test-failures
module: tests
problem_type: test_failure
component: testing_framework
severity: high
symptoms:
  - "Test suite passes (68 tests green) with no behavioral coverage for event queuing"
  - "Behavioral regressions in the queuing system produce no test failures"
  - "queue_action() helper slice [:-1] on a single-item list always produces an empty list"
root_cause: logic_error
resolution_type: test_fix
tags:
  - python
  - assert
  - test-helpers
  - silent-failure
  - slice
  - contains-unsequenced
  - queue-action
  - no-op-assertion
---

# Silent test assertions — bare contains_unsequenced() calls and wrong slice in queue_action()

## Problem

Two compounding bugs caused all assertions on queued/consumed game events to be completely inert: `contains_unsequenced()` was called as a bare expression (no `assert`) in 10 places, so Python silently discarded the boolean return value; and separately, the `queue_action()` helper used a `[:-1]` slice that always produced an empty list for a single-item queue — meaning `contains_unsequenced()` would have checked an empty list even if `assert` had been present. Neither bug produced a test failure; the entire queuing assertion layer was a no-op.

## Symptoms

- All 68 tests pass both before and after the fix — no red test run ever occurred.
- No assertion errors, no exceptions, no warnings.
- Any regression in event queuing behavior (wrong event type, missing player ID, wrong action data) would have passed silently.
- Code coverage metrics appeared healthy because the call sites executed; only the assertion result was missing.

## How It Was Found

There was no test failure. The bugs were found through code inspection — someone reading the test code noticed bare function calls that looked like they should be assertions. A linter checking for unused boolean return values would have flagged this immediately; a normal test run could not.

The two bugs were mutually concealing: the missing `assert` meant the `[:-1]` slice bug was never noticed (no `AssertionError` was raised). If `assert` had been present from the start, `assert contains_unsequenced([], ...)` would have raised `AssertionError` immediately and drawn attention to the slice problem.

## Solution

### Bug 1 — Add missing `assert` before bare `contains_unsequenced()` calls

Affected: `tests/functions/test_playing_game.py` (5 calls), `tests/functions/test_queued_action.py` (4 calls), `tests/helpers.py` (1 call).

```python
# BEFORE (no-op — return value silently discarded):
contains_unsequenced(results, {"type": "BID", "player_id": DEFAULT_ID, ...})

# AFTER (actual assertion):
assert contains_unsequenced(results, {"type": "BID", "player_id": DEFAULT_ID, ...})
```

### Bug 2 — Fix `[:-1]` slice in `queue_action()` (`tests/helpers.py`)

```python
# BEFORE — [:-1] means "all but last"; for a single-item list this is always []:
contains_unsequenced(
    queued_player["queued_actions"][:-1],   # always [] when len == 1
    {**action, "player_id": DEFAULT_ID},
)

# AFTER — [-1:] is the last element; results is the HTTP response payload.
# Combined with results[:1] to cover the case where the action was
# immediately consumed rather than held in the queue:
assert contains_unsequenced(
    [*queued_player["queued_actions"][-1:], *results[:1]],
    {**action, "player_id": DEFAULT_ID},
)
```

## Why This Works

**Bug 1 — missing `assert`:** In Python, calling a function and ignoring its return value is legal and raises no error. `contains_unsequenced()` is a pure boolean predicate; without `assert` the call executes and the `True`/`False` result is thrown away. Adding `assert` makes Python raise `AssertionError` when the predicate returns `False`, turning the call into an actual gate.

**Bug 2 — wrong slice:** `list[:-1]` is "everything except the last element". For a list of length 1 (one pending queued action — the typical case), this returns `[]`. `contains_unsequenced([], anything)` returns `False`. The fix uses `[-1:]` ("last element only", safe on any length including 0) and merges it with `results[:1]` to cover both the still-queued path and the immediately-consumed path.

## Prevention

- **Lint for unused boolean return values.** `pylint` (`W0104` / `pointless-statement`) reliably flags bare function call expressions and is the recommended tool for this today. `flake8-bugbear` `B018` also exists but its bare-function-call coverage is not yet in a released version — use `pylint` for production CI.
- **Audit predicate helpers for naked call sites.** Any helper returning `bool` used in tests (`contains_*`, `has_*`, `is_*`) is a candidate. A general-purpose grep: `rg 'contains_unsequenced\(' tests/ | grep -v 'assert\|def \|from '`.
- **Know your slice mnemonics.** `[:-1]` (all-but-last) is rarely what you want when sampling from a queue. Prefer `[-1:]` (last), `[:1]` (first), or `[0]` (first, raises on empty), and add a comment when the intent is non-obvious.
- **Verify your assertion helper can actually fail.** Write a counter-example test that intentionally passes wrong data to the helper and confirms it raises `AssertionError`. If the counter-example passes silently, the assertion is broken.

## Related Issues

- Commit `a897739` — fix: assert contains_unsequenced() results and fix queue_action check
- See also: `docs/solutions/logic-errors/queue-action-hardcoded-player-id-assertion-2026-04-09.md` — a related subsequent fix to the same helper (wrong constant in assertion dict)
