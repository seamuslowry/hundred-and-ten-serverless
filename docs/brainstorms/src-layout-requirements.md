---
date: 2026-04-09
topic: src-layout-restructure
---

# Python Source Layout Restructure

## Problem Frame

The project currently nests both application code (`src/main/`) and tests (`src/tests/`) under `src/`. This deviates from the standard Python `src` layout, which keeps tests at the repo root and uses `src/` exclusively for installable source. The deviation blurs the boundary between "what ships" and "what verifies," and violates the convention assumed by `setuptools`, `pytest`, `coverage`, and `pyright`. Since `pyproject.toml` already excludes tests from the installable package, the directory structure should reflect that intent.

## Requirements

**Application package structure**
- R1. Remove the `src/main/` wrapper. Subpackages (`auth/`, `mappers/`, `models/`, `routers/`, `services/`) move directly under `src/`, becoming `src/auth/`, `src/mappers/`, etc.
- R2. All imports of `src.main.*` update to `src.*` across all Python files in the repo (including `function_app.py` and all test files). This includes `@patch(...)` string arguments in test files — these are string literals, not import statements, and require a separate search pass. Known occurrences are in `src/tests/auth/test_firebase.py`, `src/tests/auth/test_game_exception_handler.py`, `src/tests/functions/conftest.py`, and `src/tests/helpers.py`.

**Test layout**
- R3. `src/tests/` moves to `tests/` at the repo root.
- R4. Update `from src.tests.helpers import …` references in test files to `from tests.helpers import …`. Application code under `src/` has no imports of `src.tests.*` and is unaffected.

**pyproject.toml**
- R5. `pyproject.toml` coverage omit path updates from `src/tests/*` to `tests/*`.
- R6. Confirm that `[tool.setuptools.packages.find]` with `where = ["src"]` correctly excludes `tests/` at the repo root without changes (since `tests/` will be outside the `src/` scan boundary, the existing `exclude` list is likely redundant but harmless). Update or remove the exclude entry only if confirmation shows a gap.

**CI / tooling**
- R7. `.github/workflows/coverage.yaml` step `uv run coverage run --branch --source=. -m pytest src/tests` updates to `uv run coverage run --branch --source=. -m pytest tests`.
- R8. `.vscode/settings.json` `"python.testing.pytestArgs": ["src/tests"]` updates to `"python.testing.pytestArgs": ["tests"]`.
- R9. `.funcignore` and `Dockerfile` require no changes: `.funcignore` already contains the bare pattern `tests`, which matches the future `tests/` location at repo root; `Dockerfile` uses `COPY . /home/site/wwwroot` with no path-specific references.

## Success Criteria

- `pytest` discovers and passes all existing tests from `tests/` at the repo root with no `ImportError` or `ModuleNotFoundError` during collection.
- `coverage` correctly omits `tests/` from reporting.
- `pyright` and `ruff`/`pylint` pass without new errors.
- `function_app.py` runs as before — the Azure Functions entrypoint is unaffected structurally.
- The installable package (via `uv pip install .`) contains `auth/`, `mappers/`, `models/`, `routers/`, `services/` and does not contain `tests/`.

## Scope Boundaries

- The final import prefix is `src.*` — no further renaming to `hundredandtenserverless.*` is required. The `src/` directory continues to act as the implicit package root.
- No changes to application behavior, API surface, or business logic.
- No changes to `function_app.py` structure beyond updating import paths.

## Key Decisions

- **Flatten `src/main/` rather than rename it**: The project is an Azure Functions app, not a published library. Using `src.*` imports is clean and practical; renaming to `src/hundredandtenserverless/` would add length with no user-facing benefit.
- **Tests at repo root, not inside `src/`**: Aligns with `setuptools` `where = ["src"]` convention and makes the ship/verify boundary explicit. The existing exclusion in `pyproject.toml` already signals this intent.

## Dependencies / Assumptions

- `function_app.py` must remain at the repo root — confirmed as an Azure Functions constraint.
- `src/__init__.py` exists at `src/` and will continue to serve as the package marker after `src/main/` is removed. Verify this is present at `src/` directly (not only inside `src/main/`); create it if absent as part of R1.
- The migration must be applied atomically (single commit) — `function_app.py` imports and module file locations will be inconsistent mid-migration, which would break a locally running `func start`.

## Outstanding Questions

### Deferred to Planning

- [Affects R1][Technical] Does `src/hundredandtenserverless.egg-info/` need to be deleted so it regenerates cleanly after the restructure? The current `SOURCES.txt` and `top_level.txt` already reference `src/auth/`, `src/mappers/` etc. without a `main/` prefix — verify whether this reflects a stale artifact or a prior partial migration, and confirm no files already exist at both `src/main/auth/` and `src/auth/`.
- [Affects R3][Technical] Should `[tool.pytest.ini_options]` gain `testpaths = ["tests"]` and `pythonpath = ["."]` to make headless `pytest` invocations (without an explicit path argument) work correctly after the move?

## Next Steps

-> `/ce:plan` for structured implementation planning
