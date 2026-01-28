// =============================================================================
// JohnnyBets Infrastructure - Main Orchestration
// =============================================================================
// Deploys all Azure resources for JohnnyBets
//
// Naming Convention: {prefix}-{app}-{service}-{env}-{region}
// App abbreviation: jbet
// =============================================================================

@description('Environment name')
@allowed(['dev', 'stg', 'prod'])
param environment string = 'prod'

@description('Azure region')
param location string = 'eastus2'

@description('Region abbreviation for naming')
param regionCode string = 'eus2'

@description('PostgreSQL administrator username')
param dbAdminUsername string = 'jbetadmin'

@description('PostgreSQL administrator password')
@secure()
param dbAdminPassword string

@description('OpenRouter API key')
@secure()
param openRouterApiKey string = ''

@description('The Odds API key')
@secure()
param oddsApiKey string = ''

@description('NextAuth secret')
@secure()
param nextAuthSecret string = ''

// =============================================================================
// Variables
// =============================================================================

var appName = 'jbet'
var fullAppName = 'johnnybets'

var tags = {
  environment: environment
  project: fullAppName
  managedBy: 'bicep'
}

// Resource names following convention
var names = {
  containerRegistry: 'cr${fullAppName}' // Global, no env/region
  logAnalytics: 'log-${appName}-${environment}-${regionCode}'
  keyVault: 'kv-${appName}-${environment}-${regionCode}'
  postgresql: 'psql-${appName}-${environment}-${regionCode}'
  containerAppEnv: 'cae-${appName}-${environment}-${regionCode}'
  containerApp: 'ca-${appName}-api-${environment}-${regionCode}'
  staticWebApp: 'swa-${appName}-web-${environment}-${regionCode}'
  storageAccount: 'st${appName}${environment}${regionCode}' // Conversation trace storage
}

// =============================================================================
// Resources (Direct - for listKeys/listCredentials access)
// =============================================================================

// Log Analytics Workspace
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: names.logAnalytics
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    workspaceCapping: {
      dailyQuotaGb: 1
    }
  }
}

// Container Registry
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: names.containerRegistry
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
    publicNetworkAccess: 'Enabled'
  }
}

// Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: names.keyVault
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
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

// PostgreSQL
module postgresql 'modules/postgresql.bicep' = {
  name: 'deploy-postgresql'
  params: {
    name: names.postgresql
    location: location
    tags: tags
    administratorLogin: dbAdminUsername
    administratorPassword: dbAdminPassword
    version: '16'
    skuName: 'Standard_B1ms'
    skuTier: 'Burstable'
    storageSizeGB: 32
    databaseName: fullAppName
  }
}

// Storage Account (for conversation trace logging)
module storageAccount 'modules/storageAccount.bicep' = {
  name: 'deploy-storage-account'
  params: {
    name: names.storageAccount
    location: location
    tags: tags
    skuName: 'Standard_LRS'
    containerName: 'conversations'
  }
}

// Container Apps Environment
resource containerAppEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: names.containerAppEnv
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
    zoneRedundant: false
  }
}

// Container App (API)
resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: names.containerApp
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
        corsPolicy: {
          allowedOrigins: ['*']
          allowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
          allowedHeaders: ['*']
          maxAge: 86400
        }
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          username: containerRegistry.name
          passwordSecretRef: 'registry-password'
        }
      ]
      secrets: [
        {
          name: 'registry-password'
          value: containerRegistry.listCredentials().passwords[0].value
        }
        {
          name: 'openrouter-api-key'
          value: openRouterApiKey
        }
        {
          name: 'odds-api-key'
          value: oddsApiKey
        }
        {
          name: 'database-url'
          value: 'postgresql://${dbAdminUsername}:${dbAdminPassword}@${postgresql.outputs.fqdn}:5432/${fullAppName}?sslmode=require'
        }
        {
          name: 'storage-connection-string'
          value: storageAccount.outputs.connectionString
        }
      ]
    }
    template: {
      containers: [
        {
          name: '${fullAppName}-api'
          image: '${containerRegistry.properties.loginServer}/${fullAppName}-api:latest'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'OPENROUTER_API_KEY'
              secretRef: 'openrouter-api-key'
            }
            {
              name: 'THE_ODDS_API_KEY'
              secretRef: 'odds-api-key'
            }
            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }
            {
              name: 'BETTING_AGENT_MODEL'
              value: 'x-ai/grok-4.1-fast'
            }
            {
              name: 'AZURE_STORAGE_CONNECTION_STRING'
              secretRef: 'storage-connection-string'
            }
            {
              name: 'TRACE_LOGGING_ENABLED'
              value: 'true'
            }
            {
              name: 'ENVIRONMENT'
              value: environment
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 3
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '100'
              }
            }
          }
        ]
      }
    }
  }
}

// Static Web App
resource staticWebApp 'Microsoft.Web/staticSites@2023-01-01' = {
  name: names.staticWebApp
  location: location
  tags: tags
  sku: {
    name: 'Free'
    tier: 'Free'
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

// Static Web App settings
resource staticWebAppSettings 'Microsoft.Web/staticSites/config@2023-01-01' = {
  parent: staticWebApp
  name: 'appsettings'
  properties: {
    NEXT_PUBLIC_API_URL: 'https://${containerApp.properties.configuration.ingress.fqdn}'
  }
}

// =============================================================================
// Key Vault Secrets
// =============================================================================

resource kvOpenRouterSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(openRouterApiKey)) {
  parent: keyVault
  name: 'openrouter-api-key'
  properties: {
    value: openRouterApiKey
  }
}

resource kvOddsApiSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(oddsApiKey)) {
  parent: keyVault
  name: 'odds-api-key'
  properties: {
    value: oddsApiKey
  }
}

resource kvNextAuthSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(nextAuthSecret)) {
  parent: keyVault
  name: 'nextauth-secret'
  properties: {
    value: nextAuthSecret
  }
}

resource kvDatabaseUrl 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'database-url'
  properties: {
    value: 'postgresql://${dbAdminUsername}:${dbAdminPassword}@${postgresql.outputs.fqdn}:5432/${fullAppName}?sslmode=require'
  }
}

resource kvStorageConnectionString 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'storage-connection-string'
  properties: {
    value: storageAccount.outputs.connectionString
  }
}

// =============================================================================
// Role Assignments
// =============================================================================

// Grant Container App access to Key Vault secrets
resource kvRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, names.containerApp, 'Key Vault Secrets User')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6') // Key Vault Secrets User
    principalId: containerApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// =============================================================================
// Outputs
// =============================================================================

output resourceGroupName string = resourceGroup().name
output containerRegistryLoginServer string = containerRegistry.properties.loginServer
output containerAppFqdn string = containerApp.properties.configuration.ingress.fqdn
output staticWebAppHostname string = staticWebApp.properties.defaultHostname
output postgresqlFqdn string = postgresql.outputs.fqdn
output keyVaultUri string = keyVault.properties.vaultUri
output logAnalyticsWorkspaceId string = logAnalytics.id
output storageAccountName string = storageAccount.outputs.name
output storageAccountEndpoint string = storageAccount.outputs.primaryEndpoint

// Resource names for reference
output names object = names
