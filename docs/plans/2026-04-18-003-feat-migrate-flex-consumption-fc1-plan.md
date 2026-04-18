---
title: "feat: Migrate Azure Functions app from Y1 Consumption to Flex Consumption (FC1)"
type: feat
status: completed
date: 2026-04-18
---

# feat: Migrate Azure Functions app from Y1 Consumption to Flex Consumption (FC1)

## Overview

Migrate the `hundredandten` Azure Functions app from a Linux Consumption (Y1 / Dynamic) plan to a Flex Consumption (FC1) plan. FC1 supports Python 3.13 with a current worker, eliminates the cold-start and worker-version problems that caused the current 503 outage, and uses identity-based storage authentication. This requires changes to the Terraform infrastructure, the storage account, the function app configuration, and the GitHub Actions deployment workflow.

The current outage (Python worker 4.44.0 not yet rolled out to the Y1 stamp) is the immediate driver, but FC1 is also the better long-term platform: predictable cold starts via always-ready instances, VNet integration, and no dependency on stamp-level worker rollouts.

## Problem Frame

The Y1 Consumption plan's Consumption-stamp worker (`4.1044.300`) has not received Python worker 4.44.0, which is the first version supporting Python 3.13. FC1 runs a current worker by design and is not subject to stamp-level worker rollout delays.

FC1 also imposes a breaking change on the deployment model: `WEBSITE_RUN_FROM_PACKAGE` is not supported. The deployment must switch to the FC1-native deployment API. Identity-based storage auth (no access keys) is also mandatory.

## Requirements

- R1. The function app runs Python 3.13 with `azure-functions==2.1.0` on FC1.
- R2. The staging slot exists and is independently deployable.
- R3. The GitHub Actions OIDC deploy workflow continues to work without stored secrets.
- R4. All storage authentication uses managed identity — no access keys.
- R5. Application Insights and Cosmos DB integrations are unchanged.
- R6. Deployment causes minimal downtime (acceptable: a short cutover window during plan migration).

## Scope Boundaries

- No changes to `function_app.py`, `host.json`, or application logic.
- No changes to the Cosmos DB account or Log Analytics workspace.
- The monitoring alert rule and action group are unchanged.
- The GitHub federated credential and OIDC identity remain; only the role assignment scope may change.

---

## Changes Required

### 1. Storage Account — `function.tf`

FC1 requires a StorageV2 account with TLS 1.2+ and identity-based auth. The current storage account is V1 (legacy) with TLS 1.0. **Upgrading `account_kind` from `"Storage"` to `"StorageV2"` is an in-place change** (Azure supports this upgrade without recreation); TLS version is also in-place.

```hcl
resource "azurerm_storage_account" "storage" {
  # ...
  account_kind             = "StorageV2"      # was "Storage" (V1)
  min_tls_version          = "TLS1_2"         # was "TLS1_0"
  # Remove: cross_tenant_replication_enabled (no-op on LRS)
}
```

### 2. Service Plan — `function.tf`

Change SKU from `Y1` to `FC1`. **This destroys and recreates the service plan.** The function app must be migrated to the new plan; in Terraform this means the `azurerm_linux_function_app` resource's `service_plan_id` reference will point to the new plan automatically. Terraform will likely want to recreate the function app as well — use `terraform plan` to confirm before applying.

```hcl
resource "azurerm_service_plan" "service_plan" {
  name                = "ASP-hundredandten-fc1"   # rename to avoid confusion
  resource_group_name = azurerm_resource_group.group.name
  location            = azurerm_resource_group.group.location
  os_type             = "Linux"
  sku_name            = "FC1"                     # was "Y1"
}
```

### 3. Managed Identity on the Function App — `function.tf`

FC1 requires a managed identity for storage authentication. Use a system-assigned identity for simplicity (no extra resource required).

```hcl
resource "azurerm_linux_function_app" "app" {
  # ...
  identity {
    type = "SystemAssigned"
  }
  # ...
}
```

Apply the same to the staging slot:

```hcl
resource "azurerm_linux_function_app_slot" "staging" {
  # ...
  identity {
    type = "SystemAssigned"
  }
  # ...
}
```

### 4. Storage RBAC Role Assignments — `function.tf`

Grant the function app's system-assigned identity `Storage Blob Data Owner` on the storage account. This covers secrets storage (`AzureWebJobsSecretStorageType = "Blob"`) and the internal host state blob. Repeat for the staging slot identity.

```hcl
resource "azurerm_role_assignment" "app_storage_blob" {
  scope                = azurerm_storage_account.storage.id
  role_definition_name = "Storage Blob Data Owner"
  principal_id         = azurerm_linux_function_app.app.identity[0].principal_id
}

resource "azurerm_role_assignment" "staging_storage_blob" {
  scope                = azurerm_storage_account.storage.id
  role_definition_name = "Storage Blob Data Owner"
  principal_id         = azurerm_linux_function_app_slot.staging.identity[0].principal_id
}
```

### 5. Function App Configuration — `function.tf`

Switch from access-key storage auth to identity-based, remove `FTPS`, add the storage account name env var that FC1 uses in place of a connection string.

```hcl
resource "azurerm_linux_function_app" "app" {
  name                = "hundredandten"
  resource_group_name = azurerm_resource_group.group.name
  location            = azurerm_resource_group.group.location

  https_only = true

  storage_account_name          = azurerm_storage_account.storage.name
  storage_uses_managed_identity = true          # replaces storage_account_access_key

  service_plan_id = azurerm_service_plan.service_plan.id

  identity {
    type = "SystemAssigned"
  }

  app_settings = {
    "AzureWebJobsStorage__accountName" = azurerm_storage_account.storage.name
    "AzureWebJobsSecretStorageType"    = "Blob"
    "DatabaseName"                     = "prod"
    "MongoDb"                          = azurerm_cosmosdb_account.db.primary_mongodb_connection_string
  }

  builtin_logging_enabled = false
  # client_certificate_mode removed — was never functional (requires client_certificate_enabled = true)
  # and app auth is handled by Firebase Bearer tokens

  tags = {
    "hidden-link: /app-insights-conn-string"         = azurerm_application_insights.insights.connection_string
    "hidden-link: /app-insights-instrumentation-key" = azurerm_application_insights.insights.instrumentation_key
    "hidden-link: /app-insights-resource-id"         = azurerm_application_insights.insights.id
  }

  site_config {
    application_insights_connection_string = azurerm_application_insights.insights.connection_string
    # ftps_state removed — not supported on FC1
    application_stack {
      python_version = "3.13"
    }
  }

  sticky_settings {
    app_setting_names = ["DatabaseName"]
    # Remove "CosmosDb" — it does not exist as an app_setting key; only "MongoDb" does
    # connection_string_names block removed — no connection strings defined
  }
}
```

> **Note on `sticky_settings`:** The current config references `"CosmosDb"` in both `app_setting_names` and `connection_string_names`, but the actual app setting key is `"MongoDb"` and there are no connection strings in `azurerm_linux_function_app`. This appears to be stale config. Clean it up during this migration.

Apply the equivalent changes to `azurerm_linux_function_app_slot.staging`, removing `lifecycle.ignore_changes` for `WEBSITE_RUN_FROM_PACKAGE` (that setting is not used on FC1).

### 6. GitHub RBAC Scope — `github.tf`

The current `Contributor` role assignment is scoped to the function app resource. This is sufficient for deployment. No change is required here, but verify that `Contributor` on the app includes permission to trigger the FC1 deployment API (it does — same RBAC path).

### 7. GitHub Actions Workflow — `deploy-staging.yml`

FC1 does not support `WEBSITE_RUN_FROM_PACKAGE`. The `Azure/functions-action@v1` uses that path and will not work. Switch to `v2`, which added FC1 deployment support.

Also remove the `uv pip install . --target=".python_packages/lib/site-packages"` step. FC1 supports **remote build**: you upload the source zip and Azure builds the dependencies in the cloud. This is the recommended approach and avoids the `.python_packages` path issues that caused the original Python 3.13 bug.

```yaml
- uses: actions/checkout@v4          # fix: v6 does not exist

- uses: azure/login@v3
  with:
    client-id: ${{ vars.AZURE_CLIENT_ID }}
    tenant-id: ${{ vars.AZURE_TENANT_ID }}
    subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}

- name: Deploy to staging slot
  uses: Azure/functions-action@v2    # was v1
  with:
    app-name: hundredandten
    slot-name: staging
    package: .
    respect-funcignore: true
    scm-do-build-during-deployment: true   # triggers remote build on FC1
```

The `astral-sh/setup-uv@v7` step and the `uv pip install` step are removed — dependencies are built remotely by Azure.

---

## Implementation Order

1. **Tofu — storage account** (`account_kind`, `min_tls_version`): apply first; in-place, no downtime.
2. **Tofu — service plan**: change SKU to `FC1`, rename resource. Run `tofu plan` to confirm what will be recreated.
3. **Tofu — function app + slot**: add `identity` blocks, swap storage auth, update `app_settings`, clean up `sticky_settings`, remove `ftps_state`, remove `lifecycle.ignore_changes` on `WEBSITE_RUN_FROM_PACKAGE`.
4. **Tofu — RBAC role assignments**: add `Storage Blob Data Owner` for app and slot identities.
5. **Apply in two passes** — the role assignments reference `identity[0].principal_id`, which is only known after the managed identity is created. The provider rejects unknown values for `principal_id` at plan time, so a single `tofu apply` will fail.

   **Pass 1** — create identities and migrate the plan/storage:
   ```
   tofu apply \
     -target=azurerm_storage_account.storage \
     -target=azurerm_service_plan.service_plan \
     -target=azurerm_linux_function_app.app \
     -target=azurerm_linux_function_app_slot.staging
   ```

   **Pass 2** — create role assignments now that `principal_id` values are known:
   ```
   tofu apply
   ```
6. **Update `deploy-staging.yml`**: switch to `functions-action@v2`, remove `setup-uv` and `uv pip install` steps, fix `checkout@v4`, add `scm-do-build-during-deployment: true`.
7. **Commit and push to `main`** — CI deploys to staging via the updated workflow.
8. **Verify staging**: function app reports `Running`, HTTP smoke test succeeds.
9. **Deploy to production** (manual swap or direct deploy).

## Rollback Plan

If FC1 has unexpected issues, rolling back to Y1 is a full Tofu revert (restore `sku_name = "Y1"`, restore access-key storage auth, restore the old workflow). Given that Y1 is currently 503, rollback to Y1 is not meaningfully worse than the current state. The preferred path is forward.

## Open Questions

- **`maximum_instance_count`**: FC1 defaults to 100. Consider setting a lower cap to control costs.
