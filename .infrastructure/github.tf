data "azurerm_client_config" "current" {}

resource "azurerm_user_assigned_identity" "github_deploy" {
  name                = "hundredandten-github-deploy"
  resource_group_name = azurerm_resource_group.group.name
  location            = azurerm_resource_group.group.location
}

resource "azurerm_federated_identity_credential" "github_actions" {
  name                = "github-actions"
  parent_id           = azurerm_user_assigned_identity.github_deploy.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"

  # Allows any branch push to authenticate. To restrict to a single branch,
  # change to e.g. "repo:seamuslowry/hundred-and-ten-serverless:ref:refs/heads/main"
  subject = "repo:seamuslowry/hundred-and-ten-serverless:ref:refs/heads/feat/no_publish_profile"
}

resource "azurerm_role_assignment" "github_deploy" {
  # Scoped to the staging slot only. To enable production slot swaps,
  # broaden to azurerm_linux_function_app.app.id
  scope                = azurerm_linux_function_app_slot.staging.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.github_deploy.principal_id
}

resource "github_actions_variable" "azure_client_id" {
  repository    = "hundred-and-ten-serverless"
  variable_name = "AZURE_CLIENT_ID"
  value         = azurerm_user_assigned_identity.github_deploy.client_id
}

resource "github_actions_variable" "azure_tenant_id" {
  repository    = "hundred-and-ten-serverless"
  variable_name = "AZURE_TENANT_ID"
  value         = data.azurerm_client_config.current.tenant_id
}

resource "github_actions_variable" "azure_subscription_id" {
  repository    = "hundred-and-ten-serverless"
  variable_name = "AZURE_SUBSCRIPTION_ID"
  value         = data.azurerm_client_config.current.subscription_id
}
