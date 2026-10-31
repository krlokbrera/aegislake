param(
    [Parameter(Mandatory=$true)][string]$SubscriptionId,
    [Parameter(Mandatory=$true)][string]$StorageName,
    [string]$ResourceGroup = "rg-aegislake-student",
    [switch]$CheckJob
)
$ErrorActionPreference = "Stop"

function Get-AzJson {
    param([Parameter(ValueFromRemainingArguments=$true)][string[]]$CommandArguments)
    $result = & az @CommandArguments
    if ($LASTEXITCODE -ne 0) { throw "Azure read failed. Check login, scope, RBAC and network policy." }
    return ($result | ConvertFrom-Json)
}

$account = Get-AzJson account show --subscription $SubscriptionId --output json
if ($account.state -ne "Enabled" -or $account.id -ne $SubscriptionId) {
    throw "The intended subscription is not enabled."
}
$offerUrl = "https://management.azure.com/subscriptions/${SubscriptionId}?api-version=2022-12-01"
$offer = Get-AzJson rest --method get --url $offerUrl --output json
if ($offer.subscriptionPolicies.quotaId -notmatch "(?i)student") {
    throw "Student offer not confirmed; this script does not change subscription offers."
}
$storage = Get-AzJson storage account show --subscription $SubscriptionId --resource-group $ResourceGroup --name $StorageName --output json
if ($storage.allowBlobPublicAccess -ne $false -or $storage.allowSharedKeyAccess -ne $false) {
    throw "Anonymous Blob access and Shared Key access must both be disabled."
}
if ($storage.minimumTlsVersion -ne "TLS1_2" -or $storage.enableHttpsTrafficOnly -ne $true) {
    throw "Expected HTTPS-only storage with TLS 1.2 minimum."
}
$container = Get-AzJson storage container show --account-name $StorageName --name reports --auth-mode login --output json
if ($null -eq $container.properties) { throw "Container properties could not be verified." }
$access = [string]$container.properties.publicAccess
if ($access -and $access -notin @("None", "off")) {
    throw "The reports container must be private."
}
$blobs = @(Get-AzJson storage blob list --account-name $StorageName --container-name reports --auth-mode login --output json)
$markers = @($blobs | Where-Object { $_.name -like "*/publication.json" })
if ($markers.Count -eq 0) { throw "No completed synthetic publication found; publish and verify a run first." }

$jobVerified = $null
if ($CheckJob) {
    $executions = @(Get-AzJson containerapp job execution list --subscription $SubscriptionId --resource-group $ResourceGroup --name aegislake-demo --output json)
    $successful = @($executions | Where-Object { $_.properties.status -eq "Succeeded" })
    if ($successful.Count -eq 0) { throw "No successful job execution was observed." }
    $jobVerified = $true
}
[pscustomobject]@{
    studentOfferConfirmed = $true
    storageHttpsOnly = $true
    sharedKeyDisabled = $true
    publicBlobAccessDisabled = $true
    privateContainerRead = $true
    completedPublications = $markers.Count
    optionalJobSucceeded = $jobVerified
    creditBalanceVerified = $false
    note = "Read-only configuration checks. Confirm remaining student credit separately in the portal."
} | ConvertTo-Json
