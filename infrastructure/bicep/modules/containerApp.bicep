// Azure Container App
// Runs the JohnnyBets API

@description('Name of the Container App')
param name string

@description('Azure region for deployment')
param location string

@description('Tags to apply to resources')
param tags object

@description('Container Apps Environment ID')
param containerAppEnvId string

@description('Container Registry login server')
param containerRegistryServer string

@description('Container Registry username')
param containerRegistryUsername string

@description('Container Registry password')
@secure()
param containerRegistryPassword string

@description('Container image name')
param imageName string = 'johnnybets-api'

@description('Container image tag')
param imageTag string = 'latest'

@description('Target port for the container')
param targetPort int = 8000

@description('Minimum replicas')
param minReplicas int = 0

@description('Maximum replicas')
param maxReplicas int = 3

@description('CPU cores')
param cpu string = '0.5'

@description('Memory in GB')
param memory string = '1Gi'

@description('Environment variables')
param envVars array = []

@description('Secrets for the container')
@secure()
param secrets array = []

resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppEnvId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: targetPort
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
          server: containerRegistryServer
          username: containerRegistryUsername
          passwordSecretRef: 'registry-password'
        }
      ]
      secrets: concat([
        {
          name: 'registry-password'
          value: containerRegistryPassword
        }
      ], secrets)
    }
    template: {
      containers: [
        {
          name: imageName
          image: '${containerRegistryServer}/${imageName}:${imageTag}'
          resources: {
            cpu: json(cpu)
            memory: memory
          }
          env: envVars
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: targetPort
              }
              initialDelaySeconds: 10
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: targetPort
              }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
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

output id string = containerApp.id
output name string = containerApp.name
output fqdn string = containerApp.properties.configuration.ingress.fqdn
output principalId string = containerApp.identity.principalId
