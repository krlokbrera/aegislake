# Azure for Students live verification

This review adds a read-only verification script for an existing AegisLake deployment. It confirms the student offer, storage HTTPS/TLS settings, disabled Shared Key and anonymous Blob access, a private reports container, completed publication markers and optionally a successful Container Apps Job.

Run from an authenticated Azure CLI session after reviewing `docs/AZURE.md` and deploying to the intended student subscription:

```powershell
.\scripts\verify-azure.ps1 -SubscriptionId YOUR_STUDENT_SUBSCRIPTION -StorageName YOUR_STORAGE_NAME
```

Add `-CheckJob` only if the optional job was deployed and executed. The script makes no Azure writes, does not create resources or credentials, and does not verify the remaining credit balance. A completed publication marker is an integration signal, not independent verification of report content or model effectiveness.

Pending live evidence: active student balance, quota and region, reviewed what-if, deployment result, anonymous access denial, successful authorized report read, optional job execution and observed costs. This PR remains a draft until those checks are recorded from the intended account.
