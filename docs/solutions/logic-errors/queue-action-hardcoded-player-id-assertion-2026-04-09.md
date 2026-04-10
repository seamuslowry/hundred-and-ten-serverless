---
title: "queue_action() hardcoded DEFAULT_ID in assertion instead of using player_id parameter"
date: 2026-04-09
category: logic-errors
module: tests/helpers
problem_type: logic_error
component: testing_framework
severity: medium
symptoms:
  - "No test failure observed — all 68 tests pass despite the assertion referencing the wrong value"
  - "queue_action() silently validates DEFAULT_ID regardless of the player_id argument supplied"
  - "Any future test calling queue_action() with a non-default player_id would pass even if the wrong player was queued"
root_cause: logic_error
resolution_type: test_fix
tags:
  - test-helpers
  - hardcoded-value
  - assertion-bug
  - silent-bug
  - refactor
  - python
---

# queue_action() hardcoded DEFAULT_ID in assertion instead of using player_id parameter

## Problem

The `queue_action()` helper in `tests/helpers.py` accepted a `player_id: str` parameter and correctly used it for the HTTP request and game-state lookups, but the final assertion dict hardcoded the module-level constant `DEFAULT_ID` instead of the parameter. Any future test passing a non-default player ID would silently assert the wrong value, giving a false green.

## Symptoms

- All 68 tests pass with the bug present — no immediate test failure.
- The assertion `"player_id": DEFAULT_ID` in `contains_unsequenced(...)` always resolves to `"id"` regardless of what `player_id` was passed in.
- A future test calling `queue_action(client, game_id, "other-player", action)` would pass the assertion even if `other-player`'s action was never queued, silently masking a real defect.

## How It Was Found

There was no failed test — the bug produced no test failure and was invisible through normal test runs. Every existing caller happened to pass `DEFAULT_ID` as the argument, so the hardcoded constant and the parameter always evaluated to the same string `"id"`. The bug was insidious precisely because it was silent: the test suite gave no signal that an assertion was wrong. It was surfaced by `ce:review` automated code review, cross-flagged by four independent reviewer personas (correctness, testing, maintainability, adversarial) with merged confidence 0.98.

## Solution

Replace the hardcoded `DEFAULT_ID` constant in the assertion dict with the `player_id` parameter (commit `cefb4bf`). The return type annotation was also added to bring the signature in line with other typed helpers:

**Before (buggy):**

```python
def queue_action(
    test_client: TestClient, game_id: str, player_id: str, action: dict[str, Any]
):
    ...
    assert contains_unsequenced(
        [*queued_player["queued_actions"][-1:], *results[:1]],
        {
            **action,
            "player_id": DEFAULT_ID,   # BUG: hardcoded constant, ignores parameter
        },
    )
```

**After (fixed, commit `cefb4bf`):**

```python
def queue_action(
    test_client: TestClient,
    game_id: str,
    player_id: str,
    action: dict[str, Any],
) -> dict[str, Any]:
    ...
    assert contains_unsequenced(
        [*queued_player["queued_actions"][-1:], *results[:1]],
        {
            **action,
            "player_id": player_id,   # FIXED: use parameter
        },
    )

    return results
```

## Why This Works

The parameter `player_id` was already threaded correctly into the HTTP request URL, the auth header, and the player lookup — only the final assertion dict was left behind using the old constant. By replacing `DEFAULT_ID` with `player_id`, the assertion now validates the action for whichever player the caller actually specified. The fix closes the silent assertion gap: any future test that passes a non-default player ID will correctly fail if that player's action was not queued as expected.

## Prevention

- **Use parameters, never module-level constants, inside helper assertions.** When a helper accepts a parameter that identifies the subject under test (player ID, user ID, record ID), every assertion in that helper must reference the parameter — not a convenient constant that happens to share the current value.
- **Search for constants inside assertion dicts during code review.** A pattern like `"player_id": DEFAULT_ID` inside a function that also accepts a `player_id` parameter is a strong signal of a copy-paste or refactor artifact.
- **Enable strict type checking (`mypy --strict` or `pyright` with `--disallow-untyped-defs`).** A missing return type annotation on a function that returns a value would have surfaced the incomplete review earlier. `mypy --strict` enforces return annotations on all functions, making it harder to overlook a signature during refactors.
- **Apply `ce:review` on structural refactor PRs.** This class of bug — parameter used everywhere except one spot — is easy for humans to miss after a large mechanical rename/move. Multi-persona automated review caught it here where the test suite could not.

## Related Issues

- PR #303 (`chore/split`) — structural refactor where the bug survived into the diff
