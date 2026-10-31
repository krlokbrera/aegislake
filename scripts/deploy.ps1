param(
    [Parameter(Mandatory=$true)][string]$SubscriptionId,
    [Parameter(Mandatory=$true)][string]$StorageName,
    [Parameter(Mandatory=$true)][string]$OperatorPrincipalId,
    [string]$ResourceGroup = "rg-aegislake-student",
    [string]$Location = "westeurope",
    [string]$AllowedIpAddress = "",
    [switch]$EnableJob,
    [string]$Image = "",
    [switch]$Apply
)
$ErrorActionPreference = "Stop"
function Invoke-Az {
    param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments)
    $result = & az @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Azure CLI command failed; deployment stopped." }
    return $result
}
$quota = Invoke-Az rest --method get --url "https://management.azure.com/subscriptions/$SubscriptionId?api-version=2022-12-01" --query subscriptionPolicies.quotaId -o tsv
if ($quota -notmatch "(?i)student") {
    throw "Subscription offer is not recognized as a student offer. No resources were created."
}
$state = Invoke-Az account show --subscription $SubscriptionId --query state -o tsv
if ($state -ne "Enabled") { throw "Subscription is not enabled." }
if ($EnableJob -and [string]::IsNullOrWhiteSpace($Image)) { throw "A public, pullable image is required." }
if (-not $EnableJob -and [string]::IsNullOrWhiteSpace($AllowedIpAddress)) {
    throw "Specify AllowedIpAddress for local access; the storage firewall otherwise denies it."
}
$template = Join-Path $PSScriptRoot "..\infra\main.bicep"
Invoke-Az bicep build --file $template --stdout | Out-Null
$deploymentArguments = @(
    "--subscription", $SubscriptionId, "--resource-group", $ResourceGroup,
    "--template-file", $template, "--parameters",
    "storageName=$StorageName", "operatorPrincipalId=$OperatorPrincipalId",
    "location=$Location", "allowedIpAddress=$AllowedIpAddress",
    "enableJob=$($EnableJob.IsPresent.ToString().ToLowerInvariant())", "image=$Image"
)
$exists = Invoke-Az group exists --subscription $SubscriptionId --name $ResourceGroup -o tsv
if ($exists -ne "true") {
    if (-not $Apply) {
        Write-Output "Bicep compiled and student offer checked. Resource group does not exist."
        Write-Output "Run with -Apply after reviewing docs/AZURE.md; this will create the named group."
        return
    }
    Invoke-Az group create --subscription $SubscriptionId --name $ResourceGroup --location $Location --tags project=aegislake data=synthetic-only -o none
}
Invoke-Az deployment group what-if @deploymentArguments
if ($Apply) { Invoke-Az deployment group create @deploymentArguments }
