---
title: "Pylint: raise max-instance-attributes and exclude tests from duplicate-code detection"
date: 2026-04-25
category: tooling-decisions
module: pyproject.toml
problem_type: tooling_decision
component: tooling
severity: low
applies_when:
  - "Domain model or DB document classes legitimately exceed 7 instance attributes"
  - "Test files share similar setup/assertion patterns that are intentional, not accidental duplication"
related_components:
  - testing_framework
tags:
  - pylint
  - linting
  - configuration
  - duplicate-code
  - R0801
  - design-limits
  - pyproject
---

# Pylint: raise max-instance-attributes and exclude tests from duplicate-code detection

## Context

Pylint ships with defaults tuned for typical application code. Two produce false-positive noise in this project:

1. **`max-instance-attributes` defaults to 7.** Beanie `Document` subclasses represent MongoDB documents and carry more fields than typical classes — IDs, timestamps, status, references, and domain attributes. Pylint's `R0902` fires even when the field count correctly reflects the document schema.

2. **Duplicate-code detection (`R0801`) has no path exclusions by default.** Test files legitimately repeat patterns: fixture setup, common assertions, parametrized structures. These are not structural problems. Flagging them either forces artificial extraction that harms test readability or disables a checker that is genuinely useful in application code.

## Guidance

### Raise the instance-attribute limit

Add `max-instance-attributes` to `[tool.pylint.design]` in `pyproject.toml`:

```toml
[tool.pylint.design]
# Beanie's Document class has 9 ancestors due to mixin interfaces
max-parents = 15
# Allow Settings/Config classes to have no methods (framework pattern)
min-public-methods = 0
# Beanie Document subclasses routinely carry more than the default 7 fields
max-instance-attributes = 10
```

The pylint default is **7**. Setting it to **10** accommodates typical Beanie documents without opening the door to genuinely bloated classes.

### Exclude test files from duplicate-code detection

Add a `[tool.pylint.similarities]` section:

```toml
[tool.pylint.similarities]
# Do not flag duplicate code in test files — repeated fixture and assertion
# patterns are expected and intentional, not structural duplication.
ignore-paths = ["tests/.*"]
```

`ignore-paths` takes regex patterns. `tests/.*` scopes `R0801` to `src/` and `function_app.py` only — duplicate detection in application code is preserved.

## Why This Matters

Leaving `max-instance-attributes` at 7 and suppressing inline with `# pylint: disable=too-many-instance-attributes` creates noise that reviewers learn to ignore, eroding the checker's value for catching genuinely bloated classes. Raising the limit to match domain reality keeps `R0902` signal clean.

`R0801` is a structural smell detector for production code. In tests, duplication is often correct — isolated, self-contained tests are easier to read, debug, and delete. Extracting common assertion blocks into helpers can obscure what a test actually verifies.

Do not raise `max-instance-attributes` indiscriminately. Application classes approaching 10 fields should be reviewed for decomposition opportunities before raising the limit further.

## When to Apply

- Projects using **Beanie ODM** (or another ODM/ORM whose document classes carry more than 7 fields by design).
- Projects where `R0801` fires on test files for fixture setup, parametrized assertions, or repeated helper calls rather than accidental copy-paste logic.

## Examples

**Before — pylint fires on a valid Beanie document (9 fields, limit 7):**

```python
class Game(ABC, Document):  # R0902 too-many-instance-attributes (9/7)
    name: str
    seed: int
    organizer: str
    players: list[str]
    winner_player_id: str | None
    active_player_id: str | None
    status: GameStatus
    moves: list[Move]
    accessibility: Accessibility
```

**After — `max-instance-attributes = 10` in `[tool.pylint.design]`, no inline suppression needed.**

## Related

- `pyproject.toml` — `[tool.pylint.design]` and `[tool.pylint.similarities]` sections
- pylint docs: [design checker options](https://pylint.readthedocs.io/en/stable/user_guide/checkers/design.html)
- pylint docs: [similarities checker options](https://pylint.readthedocs.io/en/stable/user_guide/checkers/similarities.html)
