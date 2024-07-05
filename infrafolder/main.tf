terraform {
  #required_version = ">=1.3.7"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>3.43.0"
    }
  }
  backend "azurerm" {
    resource_group_name = "rahultestrg"
    storage_account_name = "rahulteststorage365"
    container_name = "terraformfunctionrahul"
    key="tffunctionapprahul.tfstate"
  }
}
provider "azurerm" {
  features {
  }
}



module "createfunctionapp" {
  source = "./modules/functionapps"
  rgname = "azpoe-blobnfs-rg"
  storagename = "azpoestorageblobnfs"
  appservicename = "appserviceblobnfs"
  functionappname = "azpoe-blobnfs-monitor"
}