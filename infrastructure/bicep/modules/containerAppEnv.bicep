// Azure Container Apps Environment
// Shared environment for all Container Apps

@description('Name of the Container Apps Environment')
param name string

@description('Azure region for deployment')
param location string

@description('Tags to apply to resources')
param tags object

@description('Log Analytics workspace ID')
param logAnalyticsWorkspaceId string

@description('Log Analytics customer ID')
param logAnalyticsCustomerId string

@description('Log Analytics shared key')
@secure()
param logAnalyticsSharedKey string

resource containerAppEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsCustomerId
        sharedKey: logAnalyticsSharedKey
      }
    }
    zoneRedundant: false
  }
}

output id string = containerAppEnv.id
output name string = containerAppEnv.name
output defaultDomain string = containerAppEnv.properties.defaultDomain
