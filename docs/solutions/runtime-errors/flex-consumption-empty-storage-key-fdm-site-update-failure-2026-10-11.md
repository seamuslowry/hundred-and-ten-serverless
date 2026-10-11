---
title: "Production host-level 404s on every route — empty-key AzureWebJobsStorage broke Flex Consumption's FDM-SiteUpdateTask, so deploys silently never went live until cleanup deleted the only loadable package"
date: 2026-10-11
category: runtime-errors
module: .infrastructure/function.tf
problem_type: runtime_error
component: infrastructure
severity: critical
symptoms:
  - "Every route on hundredandten.azurewebsites.net returned 404 with an empty body and `Server: Kestrel` (Functions host 404, not a FastAPI JSON 404)"
  - "`az functionapp function list` returned nothing; the root URL still served the default 'Your Azure Function App is up and running' page"
  - "Host traces: `No functions were found... host.json file is missing from the most recent deployment`, `0 functions loaded`, and `RoutePrefix: \"api\"` (the default, meaning host.json was never read)"
  - "Host health checks: `azure.functions.webjobs.storage: Unhealthy — Unable to access AzureWebJobsStorage (AuthenticationFailed)` and 403 `Server failed to authenticate the request` on the Blob Storage Secret Repository"
  - "GitHub Actions 'Deploy to Production' reported success for the triggering commit and for the four prior commits"
  - "kudu-state.json in the deployment container showed `FDM-SiteUpdateTask: Failed` and `Kudu-SyncTriggerStep: Failed (500)` on every deployment since 2026-10-06"
root_cause: config_error
resolution_type: config_change
related_components:
  - .infrastructure/function.tf
  - .github/workflows/deploy-production.yml
  - docs/plans/2026-04-18-003-feat-migrate-flex-consumption-fc1-plan.md
tags:
  - azure-functions
  - flex-consumption
  - fc1
  - azurewebjobsstorage
  - managed-identity
  - fdm
  - kudu
  - silent-deploy-failure
  - uv-lock
---

# Production host-level 404s on every route — empty-key AzureWebJobsStorage broke Flex Consumption's FDM-SiteUpdateTask

## Problem

After dependabot commit `e701193` merged to `main` and the production deploy workflow reported success, every request to the API returned a bare 404. The commit itself (a `google-auth` version bump) was unrelated. The actual deployment mechanism had been broken for five days; this was simply the first deploy whose cleanup step deleted the stale package production had been quietly running on.

## Symptoms

- `POST /players/{id}/lobbies/search` (and every other route, including `/docs`) returned `404`, `Content-Length: 0`, `Server: Kestrel`. A FastAPI 404 would have carried a JSON body, so this was the Functions host itself with no function to route to.
- `az functionapp function list -g hundredandten -n hundredandten` returned an empty list.
- Application Insights host traces after the deploy, on every new instance:
  ```
  No functions were found. This can occur before you deploy code to your function app
  or when the host.json file is missing from the most recent deployment...
  0 functions loaded
  HttpOptions { ... "RoutePrefix": "api" }      <-- default; our host.json sets ""
  ```
- The very first host instance during the deploy *did* load `http_app_func` and executed it, but logged repeated 403s:
  ```
  Server failed to authenticate the request. Make sure the value of Authorization header
  is formed correctly including the signature. ... Status: 403
  There was an error performing a read operation on the Blob Storage Secret Repository.
  ```
  and health checks reported `azure.functions.webjobs.storage: Unhealthy ... AuthenticationFailed`.
- Kudu's post-deploy `SyncTriggers` call returned 500 ("Please run sync trigger manually").

## What Didn't Work

- **Blaming the triggering commit.** `git log --stat` showed only `pyproject.toml`/`uv.lock` changes across all 14 commits since the last known-good infra change. Rebuilding the CI package locally (`uv pip install . --target=.python_packages/lib/site-packages`) and importing `function_app` under Python 3.13 with the exact dependency set CI deployed worked and indexed `http_app_func`. The code was never the problem.
- **Trusting the GitHub Actions result.** `Azure/functions-action@v1` on Flex Consumption only checks that the package upload to the deployment container succeeded. It does not surface `FDM-SiteUpdateTask` or `SyncTriggerStep` failures. Five consecutive "successful" deploys had not changed what production was running.
- **Reading the Kudu deployment log for the first failing deploy (Oct 6).** On Flex Consumption, Kudu instances are recycled and their logs are not persisted; the API returned "The logs you are looking for were not found."
- **Checking the activity log for a config change.** Nothing but routine `publishxml/action` deploy events in the 14 days before the outage. The bad settings had been present since the FC1 migration; something changed on the platform side around Oct 5-6 that made them start mattering, which could not be determined from the available telemetry.

## Solution

### Root cause

The function app carried two app settings not managed by Terraform:

```
AzureWebJobsStorage                  = DefaultEndpointsProtocol=https;AccountName=hundredandten;AccountKey=;EndpointSuffix=core.windows.net
DEPLOYMENT_STORAGE_CONNECTION_STRING = DefaultEndpointsProtocol=https;AccountName=hundredandten;AccountKey=;EndpointSuffix=core.windows.net
```

Both had an **empty `AccountKey=`**. They were leftovers from the April FC1 migration: the migration plan intended identity-based storage (`AzureWebJobsStorage__accountName`), the `azurerm_function_app_flex_consumption` resource was configured with `storage_authentication_type = "SystemAssignedIdentity"` and the identity was granted `Storage Blob Data Owner`, but the key-based settings were never removed and the identity-based setting was never added. `tofu plan` showed no drift because the azurerm provider excludes these well-known settings from `app_settings` management.

Anything that authenticated with the managed identity (Kudu's package upload) worked. Anything that honoured those two settings (the host's secret repository, health checks, and — from Oct 6 onward — Flex's `FDM-SiteUpdateTask`) failed with 403.

### Failure chain

1. `FDM-SiteUpdateTask` is the Flex Consumption step that points the running app at the newly uploaded package. It failed on every deploy from Oct 6 to Oct 11, so the host kept loading the previous package name, `released-package.zip`. Production silently kept serving the pre-Oct-6 build while GitHub reported green deploys.
2. Kudu's `CleanUpStep` retains only the three most recent packages in the deployment container. The Oct 11 deploy was the fourth upload since the breakage, so cleanup deleted `released-package.zip` — the only blob the host could still load.
3. New host instances found no package: `0 functions loaded`, default `RoutePrefix`, host-level 404 on every URL.

Confirmed from the deployment container (`hundradandten-production`):

```
$ az storage blob list --account-name hundredandten -c hundradandten-production --auth-mode key -o table
7554b076-....zip   2026-10-08   # three GUID packages, no released-package.zip
beabab0c-....zip   2026-10-08
d27ba129-....zip   2026-10-11
kudu-state.json

$ # kudu-state.json, per deployment:
7016b789 2026-10-06 status 6 | FDM-SiteUpdate: None   | SyncTrigger: Failed
7554b076 2026-10-08 status 4 | FDM-SiteUpdate: Failed | SyncTrigger: Failed
beabab0c 2026-10-08 status 4 | FDM-SiteUpdate: Failed | SyncTrigger: Failed
d27ba129 2026-10-11 status 4 | FDM-SiteUpdate: Failed | SyncTrigger: Failed
```

The `d27ba129` zip itself was valid: `host.json`, `function_app.py`, `src/`, `.python_packages/` all at the root.

### Fix

Switch the host to identity-based storage, matching what the FC1 migration intended:

```sh
az functionapp config appsettings set -g hundredandten -n hundredandten \
  --settings AzureWebJobsStorage__accountName=hundredandten
az functionapp config appsettings delete -g hundredandten -n hundredandten \
  --setting-names AzureWebJobsStorage DEPLOYMENT_STORAGE_CONNECTION_STRING
```

Then re-ran the production deploy (`gh run rerun <id>`). With no other change, the new deployment's `kudu-state.json` showed `FDM-SiteUpdateTask: Success`, `az functionapp function list` returned `http_app_func`, and `POST /players/{id}/lobbies/search` returned `401 {"detail":"Not authenticated"}` — a FastAPI response, i.e. the app was live again on current `main`.

Codified in Terraform so the live state and the config agree (`.infrastructure/function.tf`):

```hcl
app_settings = {
  "AzureWebJobsStorage__accountName" = azurerm_storage_account.storage.name
  ...
}
```

The existing `azurerm_role_assignment.app_storage_blob` (`Storage Blob Data Owner` on the storage account) is sufficient for an HTTP-only app; queue/table roles are only needed for those trigger types.

### Related hardening in the same PR

The deploy workflow installed dependencies with `uv pip install .`, which re-resolves transitive dependencies to their newest releases and ignores `uv.lock`. Production had been getting e.g. `pydantic 2.14.0` / `starlette 1.7.0` while CI tested `2.12.5` / `1.0.0`. Changed to install from the lockfile:

```yaml
- name: Install dependencies
  run: |
    uv export --frozen --no-dev --no-hashes --no-emit-project -o "$RUNNER_TEMP/requirements.txt"
    uv pip install -r "$RUNNER_TEMP/requirements.txt" --target=".python_packages/lib/site-packages"
```

`--no-emit-project` skips installing the project package itself; `function_app.py` imports from the `src/` directory, not the installed distribution, so this is safe (verified by installing into a clean target and importing `function_app`). It also drops the stray `build/` directory from the deploy zip.

## Why This Works

Flex Consumption's deployment flow is two-phase: Kudu uploads the package to the deployment container, then the Flex Deployment Manager (FDM) updates the site to reference it. The two phases can authenticate differently. Kudu used the app's system-assigned identity (as configured on the resource) and succeeded; FDM and the Functions host honoured the explicit `AzureWebJobsStorage` / `DEPLOYMENT_STORAGE_CONNECTION_STRING` app settings, which pointed at a key-based connection string with no key, and failed with 403.

`AzureWebJobsStorage__accountName` is the Functions host's identity-based form of the storage setting: the host builds a `DefaultAzureCredential` against that account and uses the app's managed identity, which already held `Storage Blob Data Owner`. Removing the key-based settings removed the only credential path that could fail.

The delayed, deploy-count-dependent blast radius is a consequence of Kudu's package retention policy: as long as fewer than three deploys had occurred since the last successful `FDM-SiteUpdateTask`, the stale `released-package.zip` survived cleanup and production kept working on old code. The outage was deterministic once the fourth package landed.

## Prevention

- **Verify deploys at the Flex layer, not the Action layer.** `Azure/functions-action@v1` success means "uploaded", not "live". After a deploy, check `kudu-state.json` in the deployment container for `FDM-SiteUpdateTask: Success`, or at minimum `az functionapp function list` returning the expected function. Either is a one-liner against the storage account / ARM.
- **Keep host storage settings under Terraform.** Any `AzureWebJobsStorage*` or `DEPLOYMENT_STORAGE*` setting that exists on the app but not in `function.tf` is drift the provider will not report. If a key-based setting reappears, delete it; the identity path is the one that is wired up with RBAC.
- **Never leave a key-based connection string with an empty key.** It is worse than absent: components that would otherwise fall back to identity auth will instead try shared-key auth and fail.
- **Install production dependencies from `uv.lock`.** `uv pip install .` is a resolver, not an installer; use `uv export --frozen` + `uv pip install -r` so production runs the versions CI tested.
- **Expect telemetry gaps on Flex.** Kudu logs are not persisted across instance recycles and Application Insights only has data while instances are warm. `kudu-state.json` in the deployment container is the durable record of deployment-step outcomes.

## Related Issues

- `docs/plans/2026-04-18-003-feat-migrate-flex-consumption-fc1-plan.md` — the FC1 migration plan that specified `AzureWebJobsStorage__accountName`; this doc closes the gap between that plan and what was actually applied.
- `docs/solutions/runtime-errors/python-313-forward-ref-nameerror-ruff-target-version-mismatch-2026-07-29.md` — earlier incident with the same shape (green CI, broken production) caused by CI/production environment mismatch; the lockfile-pinned install here addresses another instance of that mismatch.
