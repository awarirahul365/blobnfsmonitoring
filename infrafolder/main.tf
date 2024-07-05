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
    tenant_id = "42f7676c-f455-423c-82f6-dc2d99791af7"
    subscription_id = "b437f37b-b750-489e-bc55-43044286f6e1"
    access_key = "YMyfsV3kR/UjmATRQyC20YBS8rdv1Jp5XztsUyemLp5mN/Np/RUau+6PL3oDdi5nlG5MAGJqK1xe+ASt0quDmQ=="
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