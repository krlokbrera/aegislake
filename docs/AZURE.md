# Azure for Students: deployment and verification

## Deployment status

This document is a runbook, not evidence that resources have been created. Confirm the current state in VALIDATION_STATUS.md.

## Components and boundaries

| Component | Default | Why |
| --- | --- | --- |
| StorageV2 with hierarchical namespace | Created when deployment is applied | Private report persistence |
| reports container | Private | Synthetic report access through Entra |
| Operator role assignment | Container scope | Upload without account keys |
| User-assigned managed identity | Optional | Job authentication |
| Container Apps environment | Optional, Consumption | Finite compute |
| Container Apps Job | Optional, manual only | Reproducible synthetic batch |
| Log Analytics, Sentinel, Databricks, Azure OpenAI | Not provisioned | Not required for the vertical slice |

The local lake runs inside the optional job, but bronze and silver remain ephemeral there. The job persists an allowlist of synthetic reports. Do not describe this deployment as a complete durable enterprise lake on ADLS.

## 1. Verify student access

Sign in using the official Azure CLI:

```powershell
az login
az account list --query "[].{name:name,id:id,state:state}" --output table
```

Use the intended subscription ID explicitly in every command. Inspect the student offer and available credit in the Azure portal. The deployment script checks the offer quota identifier for a student marker and refuses an unrecognized offer. That check does not measure remaining credit.

The Azure for Students offer is documented by Microsoft; your actual balance and eligibility must be checked in your own subscription. Do not convert the account to another offer to work around a failure.

## 2. Verify region, provider and permissions

Confirm the selected region supports Container Apps and that your student subscription has quota for it. The default example uses West Europe; it is not a guarantee of capacity or eligibility.

The operator needs permissions to create the named resource group and resources. Role assignments require an appropriate role-assignment permission; Contributor alone may be insufficient. The Bicep operatorPrincipalId parameter is a human user's object ID, not a client/application ID.

You can obtain your own user object ID with:

```powershell
az ad signed-in-user show --query id --output tsv
```

If your tenant blocks that lookup, obtain the object ID from the portal. Do not paste credentials or exported token files into the repository.

Register required providers in the target subscription if needed:

```powershell
az provider register --namespace Microsoft.Storage --subscription SUBSCRIPTION_ID
az provider register --namespace Microsoft.App --subscription SUBSCRIPTION_ID
az provider register --namespace Microsoft.ManagedIdentity --subscription SUBSCRIPTION_ID
```

Provider registration is a subscription change. Registration and quota provisioning are separate operations; a registered provider can still fail for quota or policy reasons.

## 3. Compile and preview storage-only mode

Choose a globally unique lowercase storage account name. Supply your current public IPv4 address as an individual address, without /32. Microsoft documents limitations on /31 and /32 CIDR rules.

```powershell
.\scripts\deploy.ps1 -SubscriptionId SUBSCRIPTION_ID -StorageName UNIQUE_STORAGE_NAME -OperatorPrincipalId YOUR_OBJECT_ID -AllowedIpAddress YOUR_PUBLIC_IPV4
```

Without -Apply the script does not create a resource group. If the group already exists it runs what-if. With -Apply it creates the named group if necessary, runs what-if, then applies the reviewed template:

```powershell
.\scripts\deploy.ps1 -SubscriptionId SUBSCRIPTION_ID -StorageName UNIQUE_STORAGE_NAME -OperatorPrincipalId YOUR_OBJECT_ID -AllowedIpAddress YOUR_PUBLIC_IPV4 -Apply
```

Use a dedicated group. A later group deletion would remove every resource in it, so do not mix unrelated resources.

## 4. Publish a verified synthetic run

```powershell
python -m pip install ".[azure]"
aegislake publish --run runs/RUN_ID --account UNIQUE_STORAGE_NAME
```

The uploader uses DefaultAzureCredential. Locally it can use your Azure CLI session. In the job it uses the assigned identity through AZURE_CLIENT_ID. No shared-key access is enabled.

A 403 can result from RBAC propagation, a wrong identity, a wrong container scope, firewall restrictions or a policy. Investigate the specific failure; do not make the container public or enable account keys to bypass it.

The uploaded allowlist is report.html, report.json, quality.json and gold/alerts.json. publication.json is written after the files complete. This commit marker is not a multi-object transaction.

## 5. Verify private access

Inspect the container access level and storage settings in the portal. Attempting anonymous Blob access should fail. Read an object using an authorized identity:

```powershell
az storage blob list --account-name UNIQUE_STORAGE_NAME --container-name reports --auth-mode login --subscription SUBSCRIPTION_ID --output table
```

Download the synthetic HTML through authenticated Azure tools, then open it locally. Do not switch on static website hosting for this private report design.

Record the deployment identifier, job execution if any, and successful private read in the evidence ledger. Keep account-specific IDs out of public screenshots where they add no value.

## 6. Optional cloud compute

Build the Docker image from the reviewed source and publish it to a registry you control. The minimal job template expects a publicly pullable image, ideally pinned by immutable digest. It does not create a registry or configure private registry credentials.

Before using a public image, inspect its layers for data and secrets. The Dockerfile copies only source and package metadata; the .dockerignore excludes local events and runs.

Apply optional compute with an existing public image:

```powershell
.\scripts\deploy.ps1 -SubscriptionId SUBSCRIPTION_ID -StorageName UNIQUE_STORAGE_NAME -OperatorPrincipalId YOUR_OBJECT_ID -EnableJob -Image PUBLIC_IMAGE_WITH_DIGEST -Apply
az containerapp job start --name aegislake-demo --resource-group rg-aegislake-student --subscription SUBSCRIPTION_ID
```

The job runs the synthetic generator and full benchmark, publishes the report, and exits. Timeout is 600 seconds, retry limit zero, replica parallelism one. Multiple separate manual starts are still possible and can multiply consumption.

Do not start the job until role assignment propagation and image availability are verified. If it fails, inspect the execution state and logs available through the platform. Central log export is disabled in this minimal template; enabling it requires a separate cost and retention decision.

Enabling the job changes storage network defaultAction to Allow because this minimal Consumption design has no fixed egress. OAuth and private container access remain mandatory. Use storage-only mode or redesign private connectivity if that tradeoff is unsuitable.

## 7. Estimate consumption before deployment

For 30 runs × 300 seconds × 0.5 vCPU, compute usage is 4,500 vCPU-seconds. At 1 GiB it is 9,000 GiB-seconds. Those figures are arithmetic, not measured runtime.

Use current regional prices and the remaining subscription-wide grants:

```powershell
python scripts/cost_model.py --runs-per-month 30 --seconds-per-run 300 --price-per-vcpu-second CURRENT_RATE --price-per-gib-second CURRENT_RATE
```

Replace CURRENT_RATE with numeric values from the official pricing calculator. The script defaults remaining free allowance to zero so it does not silently assume unused grants. Storage, transactions, network, taxes and other workloads are excluded.

Budget alerts are useful but do not automatically stop resources. Review Cost Management support for your offer and use a small dedicated budget. No email recipients or automated stop actions are created by this project.

## 8. Retention and cleanup

The template expires synthetic report blobs after 30 days, with seven-day soft deletion for blobs and containers. This can retain recoverable data and associated storage usage beyond the expiry threshold. Lifecycle actions are asynchronous.

After collecting the demonstration evidence, review the dedicated group's contents and remove only the resources you intend to retire through the Azure portal or CLI. Resource-group deletion is deliberately not automated by this repository.

## 9. CI/CD evolution

The shipped CI performs build and checks without Azure credentials. A deployment workflow should use OIDC federation, protected environments and least privilege.

For newly created repositories, verify the actual current GitHub OIDC subject format before creating federation rules; do not assume a legacy repo-name-only template. No federated credential is created by this runbook.

## Sources

- [Azure for Students](https://learn.microsoft.com/en-us/azure/education-hub/about-azure-for-students)
- [Container Apps billing](https://learn.microsoft.com/en-us/azure/container-apps/billing)
- [Container Apps Jobs](https://learn.microsoft.com/en-us/azure/container-apps/jobs)
- [Managed identities](https://learn.microsoft.com/en-us/azure/container-apps/managed-identity)
- [Blob access with Entra](https://learn.microsoft.com/en-us/azure/storage/blobs/authorize-access-azure-active-directory)
- [Storage firewall limitations](https://learn.microsoft.com/en-us/azure/storage/common/storage-network-security-limitations)
- [Cost alerts](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/cost-mgt-alerts-monitor-usage-spending)
- [OIDC with Azure](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-azure)
