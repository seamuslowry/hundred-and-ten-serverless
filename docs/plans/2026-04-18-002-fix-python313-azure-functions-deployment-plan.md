---
title: "fix: Restore Azure Functions deployment after Python 3.13 + azure-functions 2.1.0 upgrade"
type: fix
status: superceded
date: 2026-04-18
deepened: 2026-04-18
---

# fix: Restore Azure Functions deployment after Python 3.13 + azure-functions 2.1.0 upgrade

## Overview

Deployment to the Azure Functions staging slot started failing after upgrading to Python 3.13 and `azure-functions==2.1.0`. The host runtime reports `ServiceUnavailable` and the sync-trigger step fails with a "malformed content" error. The primary root cause is a known bug in the Azure Functions Python worker (fixed in worker 4.44.0, March 2026) where the `.python_packages/lib/site-packages` path was not resolved correctly on Python 3.13. The app is running on an older default worker version that predates this fix. Secondary issues include a legacy no-op app setting, a stale CI dependency reference, and package bloat in the deployed zip. No plan migration (Y1 → FC1) is required; the staging slot on the Linux Consumption plan remains.

## Problem Frame

After the Python 3.12 → 3.13 upgrade, two things changed simultaneously:
1. `azure-functions` moved from the `1.x` series to `2.x`, which requires Python ≥ 3.13 and brings a new worker model.
2. `azure-functions 2.x` on Python 3.13 uses a different worker indexing and dependency isolation mechanism, making several previously-required app settings either no-ops or actively misleading.

The most significant issue is a **known Python worker bug** fixed in worker 4.44.0 (March 25, 2026, via [PR #1833](https://github.com/Azure/azure-functions-python-worker/pull/1833)): on Python 3.13, the worker used the wrong default path when looking for customer-installed packages in `.python_packages/lib/site-packages`, causing import failures even when packages were correctly pre-installed. Without `azure-functions-runtime` in dependencies, the app runs on an older default worker that predates this fix.

Additional contributing issues:
- `AzureWebJobsFeatureFlags = "EnableWorkerIndexing"` is set in Terraform but is a no-op on Python 3.13 (worker indexing is always on); it is absent from current Azure docs as a valid value.
- The new Python 3.13 worker version control mechanism (`azure-functions-runtime` package) is not in `pyproject.toml`, leaving the app on a default worker version behind 4.44.0.
- The deployed zip includes `uv.lock`, `build/`, `dist/`, and `__pycache__/` artifacts that bloat the package.
- `actions/checkout@v6` is referenced in the CI pipeline but v6 does not exist (latest is v4).

**Note on `scm-do-build-during-deployment`:** This setting is irrelevant for this project. The repo uses OIDC/RBAC authentication, and `Azure/functions-action` only applies `scm-do-build-during-deployment` when using publish-profile (Scm) auth. On Linux Consumption with RBAC, the action uses the `WEBSITE_RUN_FROM_PACKAGE` deployment path which bypasses Kudu entirely — remote build never runs regardless of this setting.

## Requirements Trace

- R1. Deployment to the staging slot succeeds without downgrading Python (must stay on 3.13) or `azure-functions` (must stay on 2.1.0).
- R2. The staging slot function app starts and responds to HTTP requests after a successful deploy.
- R3. CI/CD pipeline changes are minimal and preserve the existing OIDC-based authentication pattern.
- R4. Terraform infrastructure changes are conservative — no plan migration, no resource replacements, only setting changes.

## Scope Boundaries

- No downgrade of Python to 3.12 or `azure-functions` to 1.x.
- No migration from Linux Consumption (Y1) to Flex Consumption (FC1) or Premium. The staging slot remains on Y1.
- No changes to application code (`function_app.py`, `src/`, business logic).
- No changes to CosmosDB, Application Insights, or networking configuration.
- No changes to the storage account kind (GPv1 → GPv2 upgrade is a separate, unrelated concern).

## Context & Research

### Relevant Code and Patterns

- `.github/workflows/deploy-staging.yml` — CI/CD pipeline; missing `scm-do-build-during-deployment: false`
- `.infrastructure/function.tf` — Terraform; contains `AzureWebJobsFeatureFlags = "EnableWorkerIndexing"` on both app and staging slot
- `pyproject.toml` — project dependencies; `azure-functions==2.1.0`, no `requirements.txt`
- `.funcignore` — package exclusions; missing `build/`, `dist/`, `uv.lock`, `__pycache__/`
- `host.json` — extension bundle `[4.*, 5.0.0)` — correct for Python v2 model
- `function_app.py` — uses `func.AsgiFunctionApp` (ASGI / Python v2 programming model)

### Institutional Learnings

- No existing `docs/solutions/` entries for Azure Functions deployment.

### External References

- [Azure Functions Python developer reference](https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python) — confirms Python 3.13+ requires `azure-functions-runtime` package for worker version control; `AzureWebJobsFeatureFlags=EnableWorkerIndexing` is no longer documented and is a no-op.
- [azure-functions 2.x release notes](https://pypi.org/project/azure-functions/) — `2.x` requires Python ≥ 3.13; no API breaking changes from 1.x; dependency isolation is always on by default.
- [Build options for Python function apps](https://learn.microsoft.com/en-us/azure/azure-functions/python-build-options) — when using pre-built local packages (`.python_packages/`), `scm-do-build-during-deployment` must be `false` to prevent Azure from overriding with a remote build.
- [GitHub: Azure/functions-action](https://github.com/Azure/functions-action) — `scm-do-build-during-deployment` is a first-class input that controls remote build; defaults to `true` when not set.

## Key Technical Decisions

- **Keep Y1 + staging slot**: The Y1 plan supports Python 3.13 today (even if it is on a retirement path for 2028) and the staging slot is functioning at the infrastructure level. The deployment failure is a worker version bug, not a plan incompatibility.
- **Add `azure-functions-runtime` to dependencies (primary fix)**: This opts the app into Python 3.13 worker version control, ensuring it runs on worker ≥ 4.44.0 which contains the critical `.python_packages` path resolution fix (PR #1833). Without this, the app runs on an older default worker that misroutes pre-installed packages.
- **Do not add `scm-do-build-during-deployment` to the CI pipeline**: The project uses OIDC/RBAC auth, under which `Azure/functions-action` uses the `WEBSITE_RUN_FROM_PACKAGE` path that bypasses Kudu entirely. The `scm-do-build-during-deployment` input is silently ignored for RBAC auth and would be misleading to add.
- **Remove `AzureWebJobsFeatureFlags` from Terraform**: On Python 3.13 + `azure-functions 2.x`, `EnableWorkerIndexing` is a no-op (not in current docs as a valid value). Removing it eliminates confusion and potential startup-path interference in future worker versions.
- **Add `lifecycle.ignore_changes` for `WEBSITE_RUN_FROM_PACKAGE` to the production app**: The staging slot already has this, but the production app does not. Without it, a `tofu apply` after CI sets `WEBSITE_RUN_FROM_PACKAGE` on the production app will cause Terraform to remove it on the next apply, breaking startup.
- **`app_settings` key removal is safe (in-place update)**: The `azurerm` v4.x provider handles `app_settings` changes as in-place updates only — no resource replacement. The app will restart but not be recreated.

## Open Questions

### Resolved During Planning

- **Does Y1 support Python 3.13?** Yes — Azure's official docs confirm Python 3.13 is GA on Functions v4 runtime. The Linux Consumption plan is on a retirement path (2028), but Python 3.13 works today. The `ServiceUnavailable` error is caused by a known worker bug, not plan incompatibility.
- **Is `scm-do-build-during-deployment` the fix?** No — the project uses OIDC/RBAC auth. Under this auth type, `Azure/functions-action` uses the `WEBSITE_RUN_FROM_PACKAGE` flow which bypasses Kudu entirely. The `scm-do-build-during-deployment` input is silently ignored (only applies to publish-profile/Scm auth). Remote build never runs in this project's deployment path.
- **What is the primary root cause?** Worker version. Python worker PR #1833 (worker 4.44.0, March 25, 2026) fixed the `.python_packages/lib/site-packages` path resolution bug on Python 3.13. Without `azure-functions-runtime` in dependencies, the app runs on an older default worker that predates this fix.
- **Is `AzureWebJobsFeatureFlags=EnableWorkerIndexing` harmful or just redundant?** It is a no-op (not listed in current docs as a supported value). Safe to remove; keeping it adds noise and may cause unpredictable behavior in future runtime versions.
- **Does removing an `app_settings` key in Terraform cause a resource replacement?** No — `azurerm_linux_function_app` (v4.x) treats `app_settings` changes as in-place updates only. The app restarts but is never recreated.

### Deferred to Implementation

- **Whether `actions/checkout@v6` silently resolves to v4 or fails outright**: Pre-existing bug. The implementer should fix it to `actions/checkout@v4` regardless.
- **Whether the production app's `WEBSITE_RUN_FROM_PACKAGE` needs `lifecycle.ignore_changes`**: Depends on whether CI ever deploys directly to production (vs. slot swap only). Inspect the existing workflow and Terraform state before deciding.
- **Whether removing `AzureWebJobsFeatureFlags` from the production app triggers any unexpected behavior**: The `tofu plan` output should confirm this as an in-place update only; verify before applying.

## Implementation Units

- [ ] **Unit 1: Add `azure-functions-runtime` to project dependencies (primary fix)**

**Goal:** Opt the app into Python 3.13 worker version control so it runs on worker ≥ 4.44.0, which contains the critical fix for `.python_packages/lib/site-packages` path resolution on Python 3.13 (PR #1833). This is the primary fix for the `ServiceUnavailable` deployment failure.

**Requirements:** R1, R2

**Dependencies:** None

**Files:**
- Modify: `pyproject.toml`

**Approach:**
- Add `azure-functions-runtime` (unpinned) to the `dependencies` list in `pyproject.toml`. Unpinned requests the latest stable worker version automatically; this is correct for a non-critical workload.
- The package is picked up by `uv pip install . --target=".python_packages/lib/site-packages"` automatically on the next CI run and included in the deployed zip.
- Without this package, Azure assigns a default (lagging) worker version that predates the 4.44.0 path resolution fix; with it, the app opts into the latest stable worker on each deploy.

**Patterns to follow:**
- Existing `dependencies` list in `pyproject.toml`

**Test scenarios:**
- Happy path: `uv pip install .` completes locally with `azure-functions-runtime` included; the package appears in `.python_packages/lib/site-packages/` after install.
- Integration: After deploy, Azure Functions runtime logs (Application Insights or live log stream) show a worker version ≥ 4.44.0.
- Integration: After deploy, the staging slot responds to HTTP requests — the `ServiceUnavailable` error is gone.
- Error path: If a dependency conflict occurs during install (unlikely given `azure-functions-runtime` has no conflicting deps), the install fails with a clear error; resolve by checking `uv lock` output.

**Verification:**
- `azure-functions-runtime` appears in the deployed package's site-packages.
- GitHub Actions deploy step completes without "Failed to perform sync trigger" error.
- Azure Functions portal for the staging slot shows the app as running (not "ServiceUnavailable").

---

- [ ] **Unit 2: Fix `actions/checkout` version pin in CI pipeline**

**Goal:** Replace the non-existent `actions/checkout@v6` reference with the current `actions/checkout@v4`, eliminating a pre-existing fragile dependency.

**Requirements:** R3

**Dependencies:** None (safe to apply independently; bundle with Unit 1)

**Files:**
- Modify: `.github/workflows/deploy-staging.yml`

**Approach:**
- Change `uses: actions/checkout@v6` to `uses: actions/checkout@v4`.
- No other workflow changes are needed. `scm-do-build-during-deployment` should NOT be added — it is irrelevant for OIDC/RBAC auth (see Key Technical Decisions).

**Patterns to follow:**
- Existing workflow structure in `.github/workflows/deploy-staging.yml`

**Test scenarios:**
- Test expectation: none — this is a pin correction on a scaffolding step with no behavioral change to the function app deployment.

**Verification:**
- Workflow run does not emit a warning about a missing or non-existent action version.

---

- [ ] **Unit 3: Remove `AzureWebJobsFeatureFlags` from Terraform app settings**

**Goal:** Remove the `EnableWorkerIndexing` feature flag from both the production app and staging slot app settings. This is a no-op on Python 3.13 and introduces noise in diagnostics.

**Requirements:** R4

**Dependencies:** None (safe to apply independently)

**Files:**
- Modify: `.infrastructure/function.tf`

**Approach:**
- Remove `"AzureWebJobsFeatureFlags" = "EnableWorkerIndexing"` from `app_settings` in both `azurerm_linux_function_app.app` (line 87) and `azurerm_linux_function_app_slot.staging` (line 131).
- Run `tofu plan` first to confirm the change is in-place only (no replacements). The `azurerm` v4.x provider always handles `app_settings` key changes as in-place updates.
- Apply during a low-traffic window; the settings change causes a brief app restart on both the production app and staging slot.
- While editing `function.tf`, also add a `lifecycle { ignore_changes = [app_settings["WEBSITE_RUN_FROM_PACKAGE"], ...] }` block to `azurerm_linux_function_app.app` (the production app) mirroring the existing block on the staging slot.

**Patterns to follow:**
- Existing `lifecycle { ignore_changes = [...] }` block on `azurerm_linux_function_app_slot.staging` (lines 154–159 of `function.tf`)

**Test scenarios:**
- Happy path: `tofu plan` shows removal of `AzureWebJobsFeatureFlags` key from both resources as in-place updates, no replacements.
- Integration: After `tofu apply`, both the production app and staging slot restart cleanly. Azure Functions portal shows both apps in "Running" state.
- Error path: If `tofu plan` shows any resource replacement, abort and investigate the azurerm provider version before proceeding.

**Verification:**
- Azure portal shows `AzureWebJobsFeatureFlags` is absent from both apps' Application Settings.
- Both apps are in "Running" state after the settings update.
- `tofu plan` on the next run shows no pending changes for these resources.

---

- [ ] **Unit 4: Tighten `.funcignore` to exclude build artifacts and lock files**

**Goal:** Reduce the deployed zip size by excluding files that are not needed at runtime.

**Requirements:** R1, R2

**Dependencies:** Unit 1 (changes take effect on next deploy)

**Files:**
- Modify: `.funcignore`

**Approach:**
- Add the following exclusions to `.funcignore`:
  - `build/` — compiled build artifacts from `setuptools`
  - `dist/` — distribution artifacts
  - `uv.lock` — lockfile; not needed at runtime
  - `__pycache__/` — Python bytecode cache directories
  - `*.egg-info` — package metadata directories
  - `docker-compose.test.yml` — test-only compose file not currently excluded
  - `htmlcov/` — coverage HTML reports if present
- Ensure `.python_packages/` is NOT accidentally excluded — it must be included for pre-built dependencies.

**Patterns to follow:**
- Existing `.funcignore` entries

**Test scenarios:**
- Happy path: After adding exclusions, inspect the deployed zip (or a local `func pack` dry run) to confirm none of the excluded paths appear.
- Edge case: Confirm `.python_packages/` remains present in the zip and is NOT accidentally matched by any new exclusion pattern.

**Verification:**
- The deployed zip does not contain `uv.lock`, `build/`, `dist/`, or `__pycache__/` at the root.
- Deploy succeeds and app starts correctly with the leaner package.

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

```
CI: push to main
  → actions/checkout@v4                    ← fix: was @v6 (non-existent)
  → setup-uv (Python 3.13)
  → uv pip install . --target=".python_packages/lib/site-packages"
     (includes azure-functions==2.1.0 + azure-functions-runtime)   ← new
  → azure/login (OIDC)
  → Azure/functions-action@v1
       (OIDC auth → WebsiteRunFromPackageDeploy path, bypasses Kudu)
       uploads zip → sets WEBSITE_RUN_FROM_PACKAGE SAS URL → syncs triggers

Azure runtime:
  → azure-functions-runtime present in package
  → worker resolves to ≥ 4.44.0 (has .python_packages path fix)   ← key fix
  → worker finds .python_packages/lib/site-packages correctly
  → AsgiFunctionApp starts cleanly, triggers sync succeeds
```

## System-Wide Impact

- **Interaction graph:** The `Azure/functions-action` sets `WEBSITE_RUN_FROM_PACKAGE` on the staging slot. The `lifecycle.ignore_changes` block on the staging slot prevents Terraform from undoing this. The production app needs the same protection (Unit 3).
- **Error propagation:** The sync-trigger call in `Azure/functions-action` occurs after the zip upload completes. If the sync still fails after this fix, the new package is already in blob storage — a manual portal restart is sufficient to recover.
- **State lifecycle risks:** Removing `AzureWebJobsFeatureFlags` from Terraform app_settings causes an in-place settings update (app restart), not a resource replacement. The `azurerm` v4.x provider confirmed to never force-replace for `app_settings` key changes.
- **Unchanged invariants:** The staging slot, the Y1 plan, the OIDC federated identity, the CosmosDB connection, the Application Insights configuration, and the ASGI programming model are all unchanged.
- **Integration coverage:** End-to-end validation is the staging slot responding to HTTP after a fresh deploy from the fixed pipeline.

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| `azure-functions-runtime` (unpinned) pulls in a pre-release worker that has regressions | Monitor the Azure Functions Python worker release notes; if a bad release is detected, pin to a known-good version |
| Worker ≥ 4.44.0 is not immediately assigned after deploy (Azure takes time to propagate worker version changes) | Wait 5–10 minutes and restart the app after deploy if `ServiceUnavailable` persists |
| `tofu apply` for Unit 3 behaves unexpectedly with the azurerm provider version in use | Always run `tofu plan` first; abort if any resource replacement appears |
| The sync-trigger failure was transient platform noise (not a worker bug), meaning Unit 1 alone may be sufficient | Units 2–4 are still worth applying; they are independent hardening changes with no deployment risk |

## Documentation / Operational Notes

- After the fix is deployed, **manually restart the staging slot** in the Azure portal if `ServiceUnavailable` persists — a cached bad state from the failed deploy can survive the new package being set.
- If the staging slot still shows `ServiceUnavailable` after Unit 1 is deployed, check the live log stream in the Azure portal for worker startup errors. Look for lines indicating the worker version in use and whether `azure-functions-runtime` was resolved.
- The `actions/checkout@v6` → `v4` fix (Unit 2) is a pre-existing bug unrelated to this failure; bundle it with Unit 1 in the same PR.
- Units 1 and 2 can be shipped in a single PR (same commit). Unit 3 (Terraform) should be applied separately via `tofu apply` after the app changes are deployed and verified.

## Sources & References

- Related code: `.github/workflows/deploy-staging.yml`, `.infrastructure/function.tf`, `pyproject.toml`, `.funcignore`
- Azure Functions Python worker fix: [PR #1833](https://github.com/Azure/azure-functions-python-worker/pull/1833) — "fix default cx deps path for 3.13" (worker 4.44.0, March 25, 2026)
- Azure Functions action auth behavior: [Azure/functions-action source](https://github.com/Azure/functions-action) — `scm-do-build-during-deployment` only applies to Scm/publish-profile auth
- External docs: [Python developer reference for Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python)
- External docs: [azure-functions PyPI releases](https://pypi.org/project/azure-functions/)
- External docs: [Terraform azurerm_linux_function_app](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/linux_function_app)
