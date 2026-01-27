// Azure Key Vault
// Secure storage for secrets, keys, and certificates

@description('Name of the Key Vault')
param name string

@description('Azure region for deployment')
param location string

@description('Tags to apply to resources')
param tags object

@description('Tenant ID for Azure AD')
param tenantId string = subscription().tenantId

@description('Object IDs that should have access to secrets')
param accessPolicies array = []

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: tenantId
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    enableRbacAuthorization: true
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
    }
  }
}

output id string = keyVault.id
output name string = keyVault.name
output uri string = keyVault.properties.vaultUri
