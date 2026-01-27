// Log Analytics Workspace
// Centralized logging for all Azure resources

@description('Name of the Log Analytics workspace')
param name string

@description('Azure region for deployment')
param location string

@description('Tags to apply to resources')
param tags object

@description('Retention period in days')
param retentionInDays int = 30

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: retentionInDays
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    workspaceCapping: {
      dailyQuotaGb: 1
    }
  }
}

output id string = logAnalytics.id
output name string = logAnalytics.name
output customerId string = logAnalytics.properties.customerId
