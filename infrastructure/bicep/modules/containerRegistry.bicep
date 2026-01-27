// Azure Container Registry
// Stores Docker images for Container Apps

@description('Name of the Container Registry')
param name string

@description('Azure region for deployment')
param location string

@description('Tags to apply to resources')
param tags object

@description('SKU for the Container Registry')
@allowed(['Basic', 'Standard', 'Premium'])
param sku string = 'Basic'

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: sku
  }
  properties: {
    adminUserEnabled: true
    publicNetworkAccess: 'Enabled'
    policies: {
      retentionPolicy: {
        days: 7
        status: 'enabled'
      }
    }
  }
}

output id string = acr.id
output name string = acr.name
output loginServer string = acr.properties.loginServer
