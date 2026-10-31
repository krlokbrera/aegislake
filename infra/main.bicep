targetScope = 'resourceGroup'

@description('Deployment region; confirm student quota and service availability first.')
param location string = resourceGroup().location

@description('Unique lowercase storage account name.')
@minLength(3)
@maxLength(24)
param storageName string

@description('Object ID of the human operator; not an application/client ID.')
param operatorPrincipalId string

@description('Deploy finite compute only after the public image exists.')
param enableJob bool = false

@description('Public, pullable image, preferably pinned by digest. Required if enableJob=true.')
param image string = ''

@description('One public IPv4 address for local upload, without /32. Empty denies local access.')
param allowedIpAddress string = ''

var tags = {
  project: 'aegislake'
  environment: 'student-demo'
  data: 'synthetic-only'
}
var blobContributor = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
)

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    isHnsEnabled: true
    accessTier: 'Hot'
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      // Consumption jobs lack fixed egress here. OAuth remains mandatory.
      defaultAction: enableJob ? 'Allow' : 'Deny'
      bypass: 'None'
      ipRules: empty(allowedIpAddress) ? [] : [
        {
          value: allowedIpAddress
          action: 'Allow'
        }
      ]
    }
  }
}
resource blobs 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 7
    }
    containerDeleteRetentionPolicy: {
      enabled: true
      days: 7
    }
  }
}
resource reports 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobs
  name: 'reports'
  properties: { publicAccess: 'None' }
}
resource lifecycle 'Microsoft.Storage/storageAccounts/managementPolicies@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: {
    policy: {
      rules: [
        {
          name: 'expire-synthetic-reports'
          enabled: true
          type: 'Lifecycle'
          definition: {
            actions: { baseBlob: { delete: { daysAfterModificationGreaterThan: 30 } } }
            filters: {
              blobTypes: ['blockBlob']
              prefixMatch: ['reports/']
            }
          }
        }
      ]
    }
  }
}
resource operatorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(reports.id, operatorPrincipalId, blobContributor)
  scope: reports
  properties: {
    principalId: operatorPrincipalId
    principalType: 'User'
    roleDefinitionId: blobContributor
  }
}
resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = if (enableJob) {
  name: 'aegislake-job-identity'
  location: location
  tags: tags
}
resource jobRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (enableJob) {
  name: guid(reports.id, identity!.id, blobContributor)
  scope: reports
  properties: {
    principalId: identity!.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: blobContributor
  }
}
resource environment 'Microsoft.App/managedEnvironments@2025-01-01' = if (enableJob) {
  name: 'aegislake-env'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: { destination: 'none' }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}
resource job 'Microsoft.App/jobs@2025-01-01' = if (enableJob) {
  name: 'aegislake-demo'
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${identity!.id}': {} }
  }
  properties: {
    environmentId: environment!.id
    workloadProfileName: 'Consumption'
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 600
      replicaRetryLimit: 0
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
    }
    template: {
      containers: [
        {
          name: 'aegislake'
          image: image
          command: [
            'python'
            '-m'
            'aegislake.cloud_job'
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'AEGIS_STORAGE_ACCOUNT'
              value: storage.name
            }
            {
              name: 'AZURE_CLIENT_ID'
              value: identity!.properties.clientId
            }
          ]
        }
      ]
    }
  }
  dependsOn: [jobRole]
}
output storageAccountName string = storage.name
output reportsContainerId string = reports.id
output jobName string = enableJob ? job!.name : ''
