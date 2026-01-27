// Azure Static Web App
// Hosts the Next.js frontend

@description('Name of the Static Web App')
param name string

@description('Azure region for deployment')
param location string

@description('Tags to apply to resources')
param tags object

@description('SKU for the Static Web App')
@allowed(['Free', 'Standard'])
param sku string = 'Free'

@description('API URL for the backend')
param apiUrl string = ''

resource staticWebApp 'Microsoft.Web/staticSites@2023-01-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: sku
    tier: sku
  }
  properties: {
    stagingEnvironmentPolicy: 'Enabled'
    allowConfigFileUpdates: true
    buildProperties: {
      appLocation: 'web'
      outputLocation: 'out'
      appBuildCommand: 'npm run build'
    }
  }
}

// App settings for the static web app
resource appSettings 'Microsoft.Web/staticSites/config@2023-01-01' = {
  parent: staticWebApp
  name: 'appsettings'
  properties: {
    NEXT_PUBLIC_API_URL: apiUrl
  }
}

output id string = staticWebApp.id
output name string = staticWebApp.name
output defaultHostname string = staticWebApp.properties.defaultHostname
output apiKey string = listSecrets(staticWebApp.id, staticWebApp.apiVersion).properties.apiKey
