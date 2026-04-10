---
title: "refactor: Restructure Python source layout — flatten src/main/, move tests to repo root"
type: refactor
status: active
date: 2026-04-09
origin: docs/brainstorms/src-layout-requirements.md
---

# refactor: Restructure Python Source Layout

## Overview

Remove the `src/main/` wrapper and move `src/tests/` to `tests/` at the repo root. After this change, the project follows the standard Python `src` layout: installable source lives directly under `src/`, tests live outside it. All imports, tooling config, and CI are updated to match.

This is a mechanical refactor with no behavioral changes. The implementation must be applied atomically — imports and file locations will be inconsistent mid-migration.

## Problem Frame

`src/main/` and `src/tests/` are both nested under `src/`, blurring the boundary between "what ships" and "what verifies." `pyproject.toml` already excludes tests from the installable package, but the directory structure contradicts that intent. `setuptools`, `pytest`, `coverage`, and `pyright` all assume tests live outside `src/`. (See origin: `docs/brainstorms/src-layout-requirements.md`)

## Requirements Trace

- R1. Remove `src/main/` wrapper; subpackages move directly under `src/`
- R2. All `src.main.*` imports update to `src.*`, including `@patch(...)` string literals
- R3. `src/tests/` moves to `tests/` at repo root
- R4. `from src.tests.helpers import …` updates to `from tests.helpers import …`
- R5. `pyproject.toml` coverage omit path updates from `src/tests/*` to `tests/*`
- R6. Confirm setuptools exclude list — no change needed (tests/ will be outside src/ scan boundary)
- R7. `.github/workflows/coverage.yaml` pytest path updates
- R8. `.vscode/settings.json` pytestArgs updates
- R9. `.funcignore` and `Dockerfile` confirmed — no changes needed

## Scope Boundaries

- No renaming to `src/hundredandtenserverless/`; final import prefix remains `src.*`
- No changes to application behavior, API surface, or business logic
- No changes to `function_app.py` structure beyond import paths

## Context & Research

### Relevant Code and Patterns

**Files to move (src/main/ → src/):**
- `src/main/auth/` → `src/auth/`
- `src/main/mappers/` → `src/mappers/`
- `src/main/models/` → `src/models/`
- `src/main/routers/` → `src/routers/`
- `src/main/services/` → `src/services/`
- Delete `src/main/__init__.py`

**Files to move (src/tests/ → tests/):**
- All 17 files under `src/tests/` → `tests/`

**Import update targets — `from src.main.` → `from src.`:**

| File | Import lines |
|------|-------------|
| `function_app.py` | Lines 12–22 (4 import statements) |
| `src/tests/helpers.py` | Lines 8–9 |
| `src/tests/mappers/test_mapper_edge_cases.py` | Lines 6–14 |
| `src/tests/functions/test_lobby_game.py` | Line 8 |
| `src/tests/functions/test_playing_game.py` | Line 5 |
| `src/tests/functions/test_queued_action.py` | Lines 5–6 |
| `src/tests/functions/conftest.py` | Line 7 |
| `src/tests/functions/test_retrieve_info.py` | Line 8 |
| `src/tests/functions/test_login.py` | Line 7 |
| `src/tests/auth/test_firebase.py` | Line 7 |
| `src/tests/auth/test_game_exception_handler.py` | Lines 8–9 |
| All files under `src/main/` (internal self-imports) | ~13 files with `from src.main.X` |

**`src.main.*` string literals (patch decorators and context managers) — separate search pass required:**

Note: some are `@patch(...)` decorators; some are `with patch(...)` context managers. Both require updating. A grep for `"src\.main\."` catches all forms.

| File | Sites | Example target |
|------|-------|---------------|
| `src/tests/auth/test_firebase.py` | Lines 13, 33, 42, 58 | `@patch("src.main.auth.firebase.id_token.verify_token")` |
| `src/tests/auth/test_game_exception_handler.py` | Lines 14, 17–18, 45–46, 59–60, 93–94, 106–107 | `@patch("src.main.auth.depends.verify_firebase_token")` |
| `src/tests/functions/conftest.py` | Line 18 | `with patch("src.main.auth.depends.verify_firebase_token", ...)` |
| `src/tests/helpers.py` | Line 29 | `with patch("src.main.auth.depends.verify_firebase_token", ...)` |

**`from src.tests.` → `from tests.` (7 import sites):**

| File | Lines |
|------|-------|
| `src/tests/auth/test_game_exception_handler.py` | Line 10 |
| `src/tests/functions/test_game_events.py` | Lines 6–14 |
| `src/tests/functions/test_queued_action.py` | Lines 7–14 |
| `src/tests/functions/test_login.py` | Line 8 |
| `src/tests/functions/test_retrieve_info.py` | Lines 9–17 |
| `src/tests/functions/test_playing_game.py` | Lines 6–15 |
| `src/tests/functions/test_lobby_game.py` | Line 9 |

**Anomalous import to fix:**
- `src/tests/functions/test_game_events.py` line 5: `from main.models.internal.constants import BidAmount, CardSuit` → `from src.models.internal.constants import BidAmount, CardSuit`

**Config files to update:**

| File | Change |
|------|--------|
| `pyproject.toml` line 45 | `"src/tests/*"` → `"tests/*"` |
| `pyproject.toml` [tool.pytest.ini_options] | Add `testpaths = ["tests"]` |
| `.github/workflows/coverage.yaml` line 20 | `pytest src/tests` → `pytest tests` |
| `.vscode/settings.json` line 13 | `"src/tests"` → `"tests"` |

**No changes needed:**
- `.funcignore` — line 4 already says `tests` (matches future location)
- `Dockerfile` — uses `COPY . /home/site/wwwroot`, no path-specific references
- `.github/workflows/lint.yaml` — uses `git ls-files '*.py'`, path-agnostic
- `.github/workflows/deploy-staging.yml` — no references to `src/tests` or `src/main`

**Delete:**
- `src/hundredandtenserverless.egg-info/` — stale artifact from a prior layout; `top_level.txt` and `SOURCES.txt` reference files that don't yet exist. Regenerates on next `uv sync` / `pip install -e .`

### Institutional Learnings

- No `docs/solutions/` exists in this repo yet.

### External References

- None required — standard Python `src` layout is well-established, and local patterns are sufficient.

## Key Technical Decisions

- **Flatten rather than rename**: `src/main/` is removed and its contents promoted to `src/` directly. Final import prefix is `src.*`. No renaming to match `pyproject.toml` project name (`hundredandtenserverless`). (See origin: `docs/brainstorms/src-layout-requirements.md`)
- **Atomic commit**: All file moves and import updates must land in a single commit. Intermediate states break `function_app.py`.
- **Add `testpaths = ["tests"]` to pytest config**: CI and `.vscode` both pass explicit paths today, but adding `testpaths` makes `uv run pytest` (bare) work correctly and removes the dependency on callers passing the path.
- **Delete stale egg-info**: `src/hundredandtenserverless.egg-info/` references the target layout, not the current one — it must be deleted before or during the restructure.
- **setuptools exclude list unchanged**: Once `tests/` is at the repo root, it is outside the `where = ["src"]` scan boundary. The existing `exclude = ["tests", "tests.*"]` becomes a no-op but is harmless and does not need updating.

## Open Questions

### Resolved During Planning

- **Does `.funcignore` need updating?** No — line 4 already contains `tests`, which matches the future `tests/` location. Confirmed by codebase inspection.
- **Does `Dockerfile` need updating?** No — uses `COPY . /home/site/wwwroot` with no path-specific references.
- **Does the setuptools `exclude` list need updating?** No — `tests/` at repo root is outside the `where = ["src"]` scan boundary; the list is redundant but harmless.
- **Does `src/__init__.py` exist?** Yes — confirmed at `src/__init__.py` (empty, directly at `src/` root). No action required.
- **What to do about the stale egg-info?** Delete `src/hundredandtenserverless.egg-info/` as part of the restructure.
- **Should `pythonpath` be added to pytest config?** No — `src/` is already importable because `src/__init__.py` exists and the repo root is on `sys.path`. Only `testpaths` is needed.
- **Anomalous import in `test_game_events.py`?** `from main.models.internal.constants import BidAmount, CardSuit` (missing `src.` prefix) must be fixed to `from src.models.internal.constants import BidAmount, CardSuit`.

### Deferred to Implementation

- None — all planning questions are resolved.

## Implementation Units

- [ ] **Unit 1: Move application subpackages from src/main/ to src/**

**Goal:** Physically relocate `auth/`, `mappers/`, `models/`, `routers/`, `services/` from `src/main/` directly under `src/`. Remove the now-empty `src/main/` directory.

**Requirements:** R1

**Dependencies:** None — first unit; all subsequent units depend on this one

**Files:**
- Move: `src/main/auth/` → `src/auth/`
- Move: `src/main/mappers/` → `src/mappers/`
- Move: `src/main/models/` → `src/models/`
- Move: `src/main/routers/` → `src/routers/`
- Move: `src/main/services/` → `src/services/`
- Delete: `src/main/__init__.py`
- Delete: `src/main/` directory (now empty)
- Delete: `src/hundredandtenserverless.egg-info/` (stale artifact)

**Approach:**
- Use `git mv` to preserve git history for moved files
- Delete `src/main/__init__.py` and the now-empty `src/main/` directory
- Delete `src/hundredandtenserverless.egg-info/` — it will regenerate on next install

**Patterns to follow:**
- `src/__init__.py` already exists at the target root — no new package marker needed

**Test scenarios:**
- Test expectation: none — this unit is a file system operation with no behavioral change; correctness is verified by Unit 3 (all tests pass)

**Verification:**
- `src/main/` no longer exists; `src/auth/`, `src/mappers/`, `src/models/`, `src/routers/`, `src/services/` exist directly under `src/`
- `src/hundredandtenserverless.egg-info/` is deleted

---

- [ ] **Unit 2: Update all src.main.* imports to src.*  (including @patch strings)**

**Goal:** Update every `from src.main.X import Y` statement and every `@patch("src.main.X...")` string literal across the entire codebase to use `src.X` instead.

**Requirements:** R2

**Dependencies:** Unit 1 (modules must exist at their new locations before imports can be validated)

**Files:**
- Modify: `function_app.py` (lines 12–22)
- Modify: `src/main/` is now `src/` — update all internal self-imports in former `src/main/` files (now at `src/auth/`, `src/models/`, `src/mappers/`, `src/routers/`, `src/services/`)
- Modify: `src/tests/helpers.py` (lines 8–9, 29)
- Modify: `src/tests/mappers/test_mapper_edge_cases.py` (lines 6–14)
- Modify: `src/tests/functions/test_lobby_game.py` (line 8)
- Modify: `src/tests/functions/test_playing_game.py` (line 5)
- Modify: `src/tests/functions/test_queued_action.py` (lines 5–6)
- Modify: `src/tests/functions/conftest.py` (lines 7, 18)
- Modify: `src/tests/functions/test_retrieve_info.py` (line 8)
- Modify: `src/tests/functions/test_login.py` (line 7)
- Modify: `src/tests/auth/test_firebase.py` (lines 7, 13, 33, 42, 58)
- Modify: `src/tests/auth/test_game_exception_handler.py` (lines 8–9, 14, 17–18, 45–46, 59–60, 93–94, 106–107)
- Fix: `src/tests/functions/test_game_events.py` line 5 (anomalous `from main.models...` → `from src.models...`)
- Test: `src/tests/` (all test files — correctness verified by running the suite)

**Approach:**
- `from src.main.X` import statements: string replacement `src.main.` → `src.`
- `@patch(...)` string literals: separate search pass — use grep for `"src.main.` to find all 11 occurrences. These are string literals, not import statements, and a plain import-statement pass will miss them.
- Anomalous import: `from main.models.internal.constants` → `from src.models.internal.constants`
- Internal self-imports within the former `src/main/` files also use `from src.main.X` — these are covered by the same replacement

**Patterns to follow:**
- After replacement, all imports in `src/auth/`, `src/models/`, etc. should use `from src.auth.X`, `from src.models.X`, etc.

**Test scenarios:**
- Test expectation: none — this unit has no behavioral change; correctness is verified by Unit 4 (all tests pass after import updates)

**Verification:**
- `grep -r "src\.main\." .` (excluding `.git/` and `docs/`) returns zero matches
- `grep -r "from main\." src/tests/` returns zero matches

---

- [ ] **Unit 3: Move src/tests/ to tests/ at repo root**

**Goal:** Physically relocate the entire test directory from `src/tests/` to `tests/` at the repo root.

**Requirements:** R3

**Dependencies:** None — can be done alongside Unit 1; import updates (Unit 4) depend on this

**Files:**
- Move: `src/tests/` → `tests/` (all 17 Python files including `__init__.py` files)

**Approach:**
- Use `git mv src/tests tests` to move the entire directory and preserve git history
- The `tests/__init__.py` (moved from `src/tests/__init__.py`) will make `tests/` a package, enabling `from tests.helpers import …`

**Test scenarios:**
- Test expectation: none — file system operation; correctness verified by Unit 4

**Verification:**
- `src/tests/` no longer exists; `tests/` exists at repo root
- `tests/__init__.py` exists (moved from `src/tests/__init__.py`)

---

- [ ] **Unit 4: Update src.tests.* imports to tests.* and fix conftest paths**

**Goal:** Update all `from src.tests.X import Y` statements to `from tests.X import Y` across the moved test files.

**Requirements:** R4

**Dependencies:** Unit 3 (test files must be at their new location)

**Files:**
- Modify: `tests/auth/test_game_exception_handler.py` (line 10)
- Modify: `tests/functions/test_game_events.py` (lines 6–14)
- Modify: `tests/functions/test_queued_action.py` (lines 7–14)
- Modify: `tests/functions/test_login.py` (line 8)
- Modify: `tests/functions/test_retrieve_info.py` (lines 9–17)
- Modify: `tests/functions/test_playing_game.py` (lines 6–15)
- Modify: `tests/functions/test_lobby_game.py` (line 9)
- Test: `tests/` (all test files)

**Approach:**
- String replacement: `from src.tests.` → `from tests.`
- 7 import sites total across 7 test files — all import from `tests.helpers`
- `tests/conftest.py` (top-level) imports `from function_app import fastapi_app` — no change needed

**Test scenarios:**
- Test expectation: none — this unit has no behavioral change; correctness verified when the full suite is run in Unit 5

**Verification:**
- `grep -r "src\.tests\." tests/` returns zero matches

---

- [ ] **Unit 5: Update configuration files**

**Goal:** Update `pyproject.toml`, `.github/workflows/coverage.yaml`, and `.vscode/settings.json` to reflect the new test path.

**Requirements:** R5, R7, R8

**Dependencies:** Units 1–4 (all file moves and import updates must be complete)

**Files:**
- Modify: `pyproject.toml`
  - Line 45: `"src/tests/*"` → `"tests/*"` (coverage omit)
  - `[tool.pytest.ini_options]`: add `testpaths = ["tests"]`
- Modify: `.github/workflows/coverage.yaml` line 20: `pytest src/tests` → `pytest tests`
- Modify: `.vscode/settings.json` line 13: `"src/tests"` → `"tests"`

**Approach:**
- Three targeted single-line (or single-section) edits; no structural changes to any config file
- `pyproject.toml` setuptools `exclude` list is left unchanged — it is now a no-op but harmless

**Test scenarios:**
- Happy path: `uv run pytest` (bare, no explicit path) discovers and runs all tests in `tests/`
- Happy path: `uv run coverage run --branch --source=. -m pytest tests` completes and `tests/` is omitted from the coverage report
- Happy path: `uv pip install .` produces an installable package containing `auth`, `mappers`, `models`, `routers`, `services` but not `tests`

**Verification:**
- `uv run pytest` discovers all tests without an explicit path argument
- `uv run coverage report --fail-under=100` passes
- `pyright` and `ruff` report no new errors

## System-Wide Impact

- **Interaction graph:** No callbacks, middleware, or observers are affected. `function_app.py` is the sole entry point and its imports are updated in Unit 2.
- **Error propagation:** Unchanged — no behavioral changes.
- **State lifecycle risks:** None — this is a rename/restructure with no data changes.
- **API surface parity:** Unchanged — no API contract changes.
- **Integration coverage:** `tests/conftest.py` imports `from function_app import fastapi_app` directly — this continues to work because `function_app.py` remains at the repo root.
- **Unchanged invariants:** All HTTP endpoints, FastAPI route definitions, Beanie ODM models, and Azure Functions ASGI wrapper behavior are unchanged.

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Mid-migration state breaks running app | Apply all changes atomically in one commit; do not push partial work |
| `@patch(...)` strings missed by import-statement search | Use a dedicated `grep -r "src\.main\."` pass after import updates to confirm zero remaining matches |
| Stale egg-info confuses tooling | Delete `src/hundredandtenserverless.egg-info/` in Unit 1; run `uv sync` after the commit |
| `test_game_events.py` anomalous import | Fix in Unit 2 alongside the other `src.main.` updates |
| pytest cannot discover `tests/` without explicit path | Mitigated by adding `testpaths = ["tests"]` in Unit 5 |

## Sources & References

- **Origin document:** [docs/brainstorms/src-layout-requirements.md](docs/brainstorms/src-layout-requirements.md)
- Related code: `function_app.py`, `pyproject.toml`, `src/main/`, `src/tests/`
- External docs: None
