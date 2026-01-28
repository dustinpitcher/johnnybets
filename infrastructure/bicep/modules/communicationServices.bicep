// =============================================================================
// Azure Communication Services with Email
// =============================================================================
// Provides email sending capabilities for transactional emails
// (password resets, invite notifications, etc.)
//
// Note: Domain must be verified before it can be linked to Communication Service.
// For Azure-managed domains, this happens automatically.
// =============================================================================

@description('Application name abbreviation')
param appName string

@description('Environment name')
param environment string

@description('Region code for naming')
param regionCode string

@description('Resource tags')
param tags object

@description('Data location for compliance')
@allowed(['UnitedStates', 'Europe', 'UK', 'Australia', 'Japan', 'France', 'Switzerland'])
param dataLocation string = 'UnitedStates'

// =============================================================================
// Email Communication Service
// =============================================================================

resource emailService 'Microsoft.Communication/emailServices@2023-03-31' = {
  name: 'es-${appName}-${environment}-${regionCode}'
  location: 'global'
  tags: tags
  properties: {
    dataLocation: dataLocation
  }
}

// =============================================================================
// Email Domain (Azure Managed)
// =============================================================================
// Using Azure-managed domain for simplicity. For production with custom domain,
// add a separate resource with domainManagement: 'CustomerManaged'

resource emailDomain 'Microsoft.Communication/emailServices/domains@2023-03-31' = {
  parent: emailService
  name: 'AzureManagedDomain'
  location: 'global'
  properties: {
    domainManagement: 'AzureManaged'
    userEngagementTracking: 'Disabled'
  }
}

// =============================================================================
// Sender Username
// =============================================================================

resource senderUsername 'Microsoft.Communication/emailServices/domains/senderUsernames@2023-03-31' = {
  parent: emailDomain
  name: 'donotreply'
  properties: {
    username: 'DoNotReply'
    displayName: 'JohnnyBets'
  }
}

// =============================================================================
// Communication Service (linked to Email Domain)
// =============================================================================

resource communicationService 'Microsoft.Communication/communicationServices@2023-03-31' = {
  name: 'acs-${appName}-${environment}-${regionCode}'
  location: 'global'
  tags: tags
  properties: {
    dataLocation: dataLocation
    linkedDomains: [
      emailDomain.id
    ]
  }
}

// =============================================================================
// Outputs
// =============================================================================

output communicationServiceName string = communicationService.name
output communicationServiceEndpoint string = 'https://${communicationService.name}.communication.azure.com'
output emailServiceName string = emailService.name

// Sender address format: username@domain.azurecomm.net
output senderAddress string = '${senderUsername.properties.username}@${emailDomain.properties.mailFromSenderDomain}'

// Connection string for SDK usage
output connectionString string = communicationService.listKeys().primaryConnectionString
