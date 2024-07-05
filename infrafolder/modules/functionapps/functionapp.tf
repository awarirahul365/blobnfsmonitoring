resource "azurerm_resource_group" "rg" {
  name     = "${var.rgname}"
  location = "West Europe"
}

resource "azurerm_storage_account" "storage" {
  name                     = "${var.storagename}"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  allow_nested_items_to_be_public = false
}

resource "azurerm_app_service_plan" "appservice" {
  name                = "${var.appservicename}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  kind                = "Linux"
  reserved            = true

  sku {
    tier = "Dynamic"
    size = "Y1"
  }
}

resource "azurerm_function_app" "functionapp" {
  name                       = "${var.functionappname}"
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  app_service_plan_id        = azurerm_app_service_plan.appservice.id
  storage_account_name       = azurerm_storage_account.storage.name
  storage_account_access_key = azurerm_storage_account.storage.primary_access_key
  os_type                    = "linux"
  version                    = "~4"
  
  site_config {
    linux_fx_version = "python|3.11"
  }
  app_settings = {
    FUNCTIONS_WORKER_RUNTIME="python"
  }
}