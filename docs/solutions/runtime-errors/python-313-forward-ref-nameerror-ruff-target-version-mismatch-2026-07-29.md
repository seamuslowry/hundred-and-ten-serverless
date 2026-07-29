---
title: "Production 502s from a NameError in Game.from_lobby() — ruff's py314 target-version masked a Python 3.13 forward-reference bug"
date: 2026-07-29
category: runtime-errors
module: src/models/internal/game.py
problem_type: runtime_error
component: tooling
severity: critical
symptoms:
  - "Production returned HTTP 502 for every request immediately after deploy"
  - "Browser devtools reported the failure as a CORS error since the crashed backend never attached response headers"
  - "Azure Functions Python worker startup log showed \"NameError: name 'Game' is not defined\" in src/models/internal/game.py at the from_lobby staticmethod"
  - "CI (lint.yaml and coverage.yaml) passed cleanly on the exact commit that crashed production"
root_cause: config_error
resolution_type: config_change
related_components:
  - .github/workflows/lint.yaml
  - .github/workflows/coverage.yaml
  - pyproject.toml
  - src/models/internal/game.py
tags:
  - python-3-13
  - python-3-14
  - pep-649
  - ruff
  - forward-references
  - ci-python-version-mismatch
  - azure-functions-cold-start
  - target-version
---

# Production 502s from a NameError in Game.from_lobby() — ruff's py314 target-version masked a Python 3.13 forward-reference bug

## Problem

The most recent production deploy caused every request to the site to fail with a 502 error, surfacing in the browser as a misleading CORS error since the FastAPI app crashed at import time before any response (or CORS headers) could ever be produced.

## Symptoms

- Every request returned 502; browser DevTools reported a CORS error, despite the app's CORS configuration never actually being the problem.
- Azure Functions Python worker startup log showed the real failure: `Microsoft.Azure.WebJobs.Script: Error building configuration in an external startup class... NameError: name 'Game' is not defined`.
- Full traceback pointed to `function_app.py` → `src/auth/__init__.py` → `src/auth/depends.py` → `src/models/internal/__init__.py` → `src/models/internal/game.py`, dying at class-body evaluation time:
  ```
  File "/home/site/wwwroot/src/models/internal/game.py", line 123, in Game
      def from_lobby(lobby: Lobby) -> Game:
  NameError: name 'Game' is not defined
  ```
- CI (lint + coverage workflows) was fully green on the exact commit that crashed production.

## What Didn't Work

- **CORS misconfiguration theory** — the app has both a FastAPI `CORSMiddleware` in `function_app.py` and a duplicate platform-level `cors` block in Terraform's `.infrastructure/function.tf`. Suspected these two configs conflicting or duplicating headers was the cause. Dead end: the app crashed during module import, before FastAPI (and therefore before `CORSMiddleware`) was ever constructed, so no CORS config was ever reached or relevant. The browser's "CORS error" was just its fallback description for a bare failed response with no headers at all.
- **Direct Azure Application Insights query** — attempted `az monitor app-insights query` to pull the real exception straight from production telemetry. Blocked by an expired interactive Azure CLI session (`AADSTS700082: refresh token expired due to inactivity`); required the user to run `az login` interactively and paste the worker startup log manually. Environmental blocker, not a false technical lead.

## Solution

Root cause: dependabot PR #368 ("chore(deps-dev): bump ruff from 0.15.22 to 0.16.0") bundled a broad `ruff --fix` pyupgrade-style cleanup pass alongside the version bump, which stripped the quotes from a self-referential forward-reference return annotation:

```python
# Before (broken by PR #368 / commit 420f216)
class Game(BaseGame):
    ...
    @staticmethod
    def from_lobby(lobby: Lobby) -> Game:
        ...
```

```python
# After (fix)
class Game(BaseGame):
    ...
    @staticmethod
    def from_lobby(lobby: Lobby) -> "Game":
        ...
```

Every other change in that same commit was safe (e.g. `Optional[X]` → `X | None` on already-bound names like `PlayerInGame`, `Action`, `str`); this one self-referential annotation was the only unsafe rewrite.

Confirmed empirically, not just by inspection:

```sh
git stash                                                    # remove the fix
uv run --python 3.13 python -c "import src.models.internal.game"
# -> NameError: name 'Game' is not defined  (reproduces prod crash exactly)

git stash pop                                                # restore -> "Game"
uv run --python 3.13 python -c "import src.models.internal.game"
# -> import OK
```

The linter config itself was still a hazard even after fixing the line — `ruff check` under `target-version = "py314"` immediately re-flagged the restored quotes with `UP037: Remove quotes from type annotation`, meaning any future `ruff --fix` pass would silently reintroduce the exact same crash. So the deeper fix aligned the toolchain's target version with the real deployed runtime:

```diff
 [tool.ruff]
-target-version = "py314"
+target-version = "py313"

 [tool.black]
-target-version = ["py314"]
+target-version = ["py313"]
```

And pinned CI to actually run under that same interpreter:

```diff
 # .github/workflows/lint.yaml and .github/workflows/coverage.yaml
       - uses: astral-sh/setup-uv@v7
         with:
           enable-cache: true
+          python-version: "3.13"
```

With `target-version = "py313"`, `ruff check .` and `black --check .` pass cleanly with the quotes in place (no more `UP037`). Full lint suite (pylint, pyright, ruff, black) and full test suite (91 tests, `coverage run -m pytest tests` + `coverage report --fail-under=100`) pass under Python 3.13 against the Mongo test container, maintaining 100% branch coverage. Merged as PR #371 on branch `fix/game-forward-ref-nameerror-py313`.

## Why This Works

The behavior hinges on how Python evaluates function annotations at class-definition time. Prior to PEP 649, annotations in a function signature (`def from_lobby(lobby: Lobby) -> Game:`) are evaluated *eagerly*, at the moment the `def` statement executes — which happens while the enclosing `class Game(BaseGame):` body is still being built. At that point, the name `Game` does not exist yet in any enclosing scope (it's only bound in the module namespace *after* the class statement fully finishes), so an unquoted `-> Game` reference to the class being defined raises `NameError: name 'Game' is not defined`. Quoting the annotation (`-> "Game"`) or using `from __future__ import annotations` defers evaluation of the string/annotation, sidestepping the ordering problem entirely — this is the standard idiom for self-referential type hints.

Python 3.14 ships PEP 649 (deferred evaluation of annotations) as the default behavior: annotations become lazily evaluated closures rather than eagerly executed expressions, so the same unquoted `-> Game` code runs without error under 3.14. This is exactly why ruff's `UP037` rule (configured for `target-version = "py314"`) considered the quotes unnecessary and stripped them — the rule is *correct* for Python 3.14 semantics, but the code was never actually going to run on 3.14 in production.

The project's actual deployed runtime is Python 3.13 (per `.github/workflows/deploy-production.yml` and `.infrastructure/function.tf`), which does not have PEP 649 deferred evaluation by default. But `pyproject.toml` only declared `requires-python = ">=3.13"` with no upper bound, and neither `lint.yaml` nor `coverage.yaml` pinned a `python-version` for `astral-sh/setup-uv`. As a result, `uv` silently resolved the newest interpreter satisfying that constraint — Python 3.14 — for every CI run. CI was therefore validating the code under different annotation-evaluation semantics than production actually uses, so a change that is a no-op under 3.14 (stripping the quotes) but a hard crash under 3.13 sailed through every lint and test gate untouched, and only surfaced when the Azure Functions host loaded the module under the real 3.13 runtime.

## Prevention

- **Pin CI Python versions to match the deployed runtime, always.** Never let `uv`/`setup-uv` (or any interpreter-resolution step) silently pick "newest available" — explicitly pin `python-version` in every workflow that lints, tests, or otherwise validates code destined for production, matching the version declared in the deploy workflow and Terraform (`.infrastructure/function.tf`) exactly.
- **Keep `ruff`/`black` `target-version` set to the real deployed Python version, not the newest toolchain available locally.** Treat `target-version` as a statement of "what semantics must this code be correct under," not "what's the latest thing my linter supports" — a mismatch here means the linter can actively rewrite code into a form that's only valid under a version you don't actually run.
- **Consider adding `from __future__ import annotations` project-wide** as defense-in-depth. This defers all annotation evaluation regardless of interpreter version, so self-referential forward references (and similar ordering issues) can never cause an eager-evaluation `NameError` again, independent of whatever `target-version` ruff/black are configured with. This is a suggestion for follow-up, not something done as part of this fix.
- **Add a lightweight import/smoke-test step to the deploy workflow** that runs something like `python -c "import function_app"` under the exact Python version used by the deployed Function App, before (or immediately after) deploying. This class of import-time `NameError` crash happens at module load, before any test fixture or FastAPI `TestClient` request is even possible — so it can bypass 100%-branch-coverage test suites entirely if those suites run under a different interpreter than production, as happened here.

## Related Issues

- No related GitHub issues found (`gh issue list --search "CORS 502 NameError Game" --state all --limit 5` returned no results).
- `docs/solutions/logic-errors/game-rounds-action-replay-boundary-and-score-aggregation-bugs-2026-04-24.md` also touches `src/models/internal/game.py` and references Python 3.14 (for `match`/`case` coverage-pragma behavior), but for an unrelated reason. Worth cross-referencing: this repo's CI silently ran under Python 3.14 for a period due to the unpinned `python-version` described here, so any prior Python-3.14-specific observations in that doc should be re-verified now that CI and production both run 3.13.
- PR: https://github.com/seamuslowry/hundred-and-ten-serverless/pull/371
