targetScope = 'resourceGroup'

param location string = 'polandcentral'
param managerSize string = 'Standard_B4als_v2'
param endpointSize string = 'Standard_B2ats_v2'
param sshPublicKey string
param adminUsername string = 'aegisadmin'
param imageVersion string = '24.04.202610210'
param managerCloudConfig string
param endpointCloudConfig string

var nodes = [
  { name: 'aegis-wazuh', size: managerSize, ip: '10.77.0.4', disk: 64, data: managerCloudConfig }
  { name: 'aegis-endpoint', size: endpointSize, ip: '10.77.0.5', disk: 32, data: endpointCloudConfig }
]
var tags = { project: 'aegislake', environment: 'student-lab', data: 'lab-events' }

resource nsg 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: 'nsg-aegislake-lab'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'AgentToWazuh'
        properties: {
          priority: 100
          protocol: 'Tcp'
          access: 'Allow'
          direction: 'Inbound'
          sourceAddressPrefix: '10.77.0.5'
          sourcePortRange: '*'
          destinationAddressPrefix: '10.77.0.4'
          destinationPortRanges: ['1514', '1515']
        }
      }
      {
        name: 'LabSshSimulationOnly'
        properties: {
          priority: 110
          protocol: 'Tcp'
          access: 'Allow'
          direction: 'Inbound'
          sourceAddressPrefix: '10.77.0.4'
          sourcePortRange: '*'
          destinationAddressPrefix: '10.77.0.5'
          destinationPortRange: '22'
        }
      }
      {
        name: 'DenyOtherInbound'
        properties: {
          priority: 4000
          protocol: '*'
          access: 'Deny'
          direction: 'Inbound'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
        }
      }
    ]
  }
}
resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: 'vnet-aegislake-lab'
  location: location
  tags: tags
  properties: {
    addressSpace: { addressPrefixes: ['10.77.0.0/24'] }
    subnets: [
      {
        name: 'lab'
        properties: {
          addressPrefix: '10.77.0.0/24'
          networkSecurityGroup: { id: nsg.id }
          // Explicit lab-only outbound access; no public ingress or paid NAT.
          defaultOutboundAccess: true
        }
      }
    ]
  }
}
resource nics 'Microsoft.Network/networkInterfaces@2024-05-01' = [for node in nodes: {
  name: 'nic-${node.name}'
  location: location
  tags: tags
  properties: {
    enableAcceleratedNetworking: false
    ipConfigurations: [
      {
        name: 'primary'
        properties: {
          privateIPAllocationMethod: 'Static'
          privateIPAddress: node.ip
          subnet: { id: '${vnet.id}/subnets/lab' }
        }
      }
    ]
  }
}]
resource vms 'Microsoft.Compute/virtualMachines@2024-07-01' = [for (node, i) in nodes: {
  name: node.name
  location: location
  tags: tags
  properties: {
    hardwareProfile: { vmSize: node.size }
    securityProfile: {
      securityType: 'TrustedLaunch'
      uefiSettings: { secureBootEnabled: true, vTpmEnabled: true }
    }
    osProfile: {
      computerName: node.name
      adminUsername: adminUsername
      customData: base64(node.data)
      linuxConfiguration: {
        disablePasswordAuthentication: true
        provisionVMAgent: true
        ssh: {
          publicKeys: [
            { path: '/home/${adminUsername}/.ssh/authorized_keys', keyData: sshPublicKey }
          ]
        }
      }
    }
    storageProfile: {
      imageReference: {
        publisher: 'Canonical'
        offer: 'ubuntu-24_04-lts'
        sku: 'server'
        version: imageVersion
      }
      osDisk: {
        name: 'disk-${node.name}'
        createOption: 'FromImage'
        diskSizeGB: node.disk
        managedDisk: { storageAccountType: 'StandardSSD_LRS' }
        deleteOption: 'Detach'
      }
    }
    networkProfile: {
      networkInterfaces: [
        { id: nics[i].id, properties: { primary: true, deleteOption: 'Detach' } }
      ]
    }
    diagnosticsProfile: { bootDiagnostics: { enabled: false } }
  }
}]
output managerPrivateIp string = '10.77.0.4'
output endpointPrivateIp string = '10.77.0.5'
