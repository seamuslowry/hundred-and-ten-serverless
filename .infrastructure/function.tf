resource "azurerm_resource_group" "group" {
  name     = "hundredandten"
  location = "eastus"
}

resource "azurerm_storage_account" "storage" {
  name                     = "hundredandten"
  resource_group_name      = azurerm_resource_group.group.name
  location                 = azurerm_resource_group.group.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  min_tls_version          = "TLS1_2"
}

resource "azurerm_service_plan" "service_plan" {
  name                = "ASP-hundredandten-fc1"
  resource_group_name = azurerm_resource_group.group.name
  location            = azurerm_resource_group.group.location
  os_type             = "Linux"
  sku_name            = "FC1"

  lifecycle {
    create_before_destroy = true
  }
}

resource "azurerm_log_analytics_workspace" "workspace" {
  name                = "workspace-hundredandten"
  location            = azurerm_resource_group.group.location
  resource_group_name = azurerm_resource_group.group.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_application_insights" "insights" {
  name                = "hundredandten"
  location            = azurerm_resource_group.group.location
  resource_group_name = azurerm_resource_group.group.name
  application_type    = "web"
  sampling_percentage = 0
  workspace_id        = azurerm_log_analytics_workspace.workspace.id
}

resource "azurerm_cosmosdb_account" "db" {
  name                = "hundred-and-ten-mongo"
  location            = azurerm_resource_group.group.location
  resource_group_name = azurerm_resource_group.group.name
  offer_type          = "Standard"
  kind                = "MongoDB"

  automatic_failover_enabled = false

  capabilities {
    name = "DisableRateLimitingResponses"
  }

  capabilities {
    name = "EnableServerless"
  }

  capabilities {
    name = "EnableMongo"
  }

  consistency_policy {
    consistency_level       = "Session"
    max_interval_in_seconds = 5
    max_staleness_prefix    = 100
  }

  geo_location {
    location          = azurerm_resource_group.group.location
    failover_priority = 0
  }
}

resource "azurerm_linux_function_app" "app" {
  name                = "hundredandten"
  resource_group_name = azurerm_resource_group.group.name
  location            = azurerm_resource_group.group.location

  https_only = true

  storage_account_name          = azurerm_storage_account.storage.name
  storage_uses_managed_identity = true
  service_plan_id               = azurerm_service_plan.service_plan.id

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

  tags = {
    "hidden-link: /app-insights-conn-string"         = azurerm_application_insights.insights.connection_string
    "hidden-link: /app-insights-instrumentation-key" = azurerm_application_insights.insights.instrumentation_key
    "hidden-link: /app-insights-resource-id"         = azurerm_application_insights.insights.id
  }

  site_config {
    application_insights_connection_string = azurerm_application_insights.insights.connection_string
    application_stack {
      python_version = "3.13"
    }
  }

  sticky_settings {
    app_setting_names = ["DatabaseName"]
  }
}

resource "azurerm_linux_function_app_slot" "staging" {
  name                 = "staging"
  function_app_id      = azurerm_linux_function_app.app.id

  https_only = true

  storage_account_name          = azurerm_storage_account.storage.name
  storage_uses_managed_identity = true

  identity {
    type = "SystemAssigned"
  }

  app_settings = {
    "AzureWebJobsStorage__accountName" = azurerm_storage_account.storage.name
    "AzureWebJobsSecretStorageType"    = "Blob"
    "DatabaseName"                     = "dev"
    "MongoDb"                          = azurerm_cosmosdb_account.db.primary_mongodb_connection_string
  }

  builtin_logging_enabled = false

  tags = {
    "hidden-link: /app-insights-conn-string"         = azurerm_application_insights.insights.connection_string
    "hidden-link: /app-insights-instrumentation-key" = azurerm_application_insights.insights.instrumentation_key
    "hidden-link: /app-insights-resource-id"         = azurerm_application_insights.insights.id
  }

  site_config {
    application_insights_connection_string = azurerm_application_insights.insights.connection_string
    application_stack {
      python_version = "3.13"
    }
  }
}

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

data "azurerm_role_definition" "monitoring_contributor" {
  name     = "Monitoring Contributor"
}

data "azurerm_role_definition" "monitoring_reader" {
  name     = "Monitoring Reader"
}

resource "azurerm_monitor_action_group" "action_group" {
  name                = "Application Insights Smart Detection"
  resource_group_name = azurerm_resource_group.group.name
  short_name          = "SmartDetect"

  arm_role_receiver {
    name                    = "Monitoring Contributor"
    # need just the UUID at the end of this ID
    role_id                 = regex("^.*/([^/]+)$", data.azurerm_role_definition.monitoring_contributor.id)[0]
    use_common_alert_schema = true
  }
  arm_role_receiver {
    name                    = "Monitoring Reader"
    # need just the UUID at the end of this ID
    role_id                 = regex("^.*/([^/]+)$", data.azurerm_role_definition.monitoring_reader.id)[0]
    use_common_alert_schema = true
  }
}

resource "azurerm_monitor_smart_detector_alert_rule" "detection_rule" {
  name                   = "Failure Anomalies - hundredandten"
  description            = "Failure Anomalies notifies you of an unusual rise in the rate of failed HTTP requests or dependency calls."
  resource_group_name    = azurerm_resource_group.group.name
  scope_resource_ids     = [azurerm_application_insights.insights.id]
  severity               = "Sev3"
  frequency              = "PT1M"
  detector_type          = "FailureAnomaliesDetector"

  action_group {
    ids = [azurerm_monitor_action_group.action_group.id]
  }

  enabled = true
}
