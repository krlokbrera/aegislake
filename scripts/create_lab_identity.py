"""Create the approved Automation identity and narrowly scoped lab roles.

Run only after approving these new access grants. Uses the operator's Azure CLI
session and never prints or persists access tokens. Does not create VMs or jobs.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import urllib.request
import urllib.error
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subscription", required=True)
    parser.add_argument("--billing-profile", required=True)
    parser.add_argument("--control-region", default="spaincentral")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--standalone", action="store_true", help="Create a user-assigned guard identity when Automation is unavailable")
    args = parser.parse_args()
    if not args.billing_profile.startswith("/providers/Microsoft.Billing/billingAccounts/"):
        raise ValueError("Expected a billing profile ARM ID")
    if "/billingProfiles/" not in args.billing_profile or "?" in args.billing_profile:
        raise ValueError("Expected a single billing profile")
    sub = "/subscriptions/" + str(uuid.UUID(args.subscription))
    lab = sub + "/resourceGroups/rg-aegislake-lab"
    control = sub + "/resourceGroups/rg-aegislake-control"
    account = control + "/providers/Microsoft.Automation/automationAccounts/aa-aegislake-creditguard"
    if args.standalone:
        account = control + "/providers/Microsoft.ManagedIdentity/userAssignedIdentities/mi-aegislake-creditguard"
    actions = [
        "Microsoft.Compute/virtualMachines/read",
        "Microsoft.Compute/virtualMachines/instanceView/read",
        "Microsoft.Compute/virtualMachines/deallocate/action",
    ]
    if not args.apply:
        print(json.dumps({"account":account, "labScope":lab, "actions":actions,
                          "billingRole":"Billing profile reader"}, indent=2))
        return
    token = subprocess.check_output(
        ["az", "account", "get-access-token", "--subscription", args.subscription,
         "--query", "accessToken", "-o", "tsv"], text=True
    ).strip()

    def request(method, path, version, body=None):
        url = "https://management.azure.com" + path + "?api-version=" + version
        headers = {"Authorization":"Bearer " + token}
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                raw = response.read()
                return (json.loads(raw) if raw else {}), dict(response.headers)
        except urllib.error.HTTPError as exc:
            document = json.loads(exc.read())
            detail = document.get("error", document)
            raise RuntimeError(str(exc.code) + ": " + detail.get("code","AzureError")
                               + ": " + detail.get("message","Request failed")) from None

    account_state = json.loads(subprocess.check_output(
        ["az", "account", "show", "--subscription", args.subscription, "-o", "json"], text=True
    ))
    if account_state["state"] != "Enabled":
        raise RuntimeError("Subscription is not enabled")
    for scope, region in [(lab, "spaincentral"), (control, args.control_region)]:
        try:
            group, _ = request("GET", scope, "2022-09-01")
            if group.get("tags", {}).get("project") != "aegislake":
                raise RuntimeError("Refusing to reuse an unrelated resource group")
        except RuntimeError as error:
            if not str(error).startswith("404:"):
                raise
            group, _ = request("PUT", scope, "2022-09-01",
                {"location":region, "tags":{"project":"aegislake","purpose":"student-lab"}})
        print("Resource group ready:", group["name"], flush=True)
    if args.standalone:
        resource, _ = request("PUT", account, "2023-01-31", {
            "location":args.control_region,
            "tags":{"project":"aegislake","purpose":"credit-guard"},
        })
        principal = resource["properties"]["principalId"]
        tenant = resource["properties"]["tenantId"]
    else:
        resource, _ = request("PUT", account, "2024-10-23", {
            "location":args.control_region,
            "identity":{"type":"SystemAssigned"},
            "properties":{"sku":{"name":"Basic"},"disableLocalAuth":True,
                          "publicNetworkAccess":False},
            "tags":{"project":"aegislake","purpose":"credit-guard"},
        })
        principal = resource["identity"]["principalId"]
        tenant = resource["identity"]["tenantId"]
    print("Guard identity created:", principal, flush=True)
    role_id = str(uuid.uuid5(uuid.NAMESPACE_URL, lab + "/AegisLake-Lab-Deallocator"))
    role_path = sub + "/providers/Microsoft.Authorization/roleDefinitions/" + role_id
    role, _ = request("PUT", role_path, "2022-04-01", {
        "properties":{
            "roleName":"AegisLake Lab Deallocator",
            "description":"Read and deallocate only VMs in the dedicated AegisLake lab group.",
            "type":"CustomRole",
            "permissions":[{"actions":actions,"notActions":[],"dataActions":[],"notDataActions":[]}],
            "assignableScopes":[lab],
        }
    })
    assignment_id = str(uuid.uuid5(uuid.NAMESPACE_URL, lab + principal + role_id))
    assignment, _ = request("PUT", lab + "/providers/Microsoft.Authorization/roleAssignments/"
                            + assignment_id, "2022-04-01", {
        "properties":{"principalId":principal,"principalType":"ServicePrincipal",
                      "roleDefinitionId":role["id"]}
    })
    print("Scoped VM deallocation permission assigned.", flush=True)
    definitions, _ = request("GET", args.billing_profile + "/billingRoleDefinitions", "2024-04-01")
    readers = [r for r in definitions["value"]
               if r["properties"]["roleName"] == "Billing profile reader"]
    if len(readers) != 1:
        raise RuntimeError("Exactly one billing profile reader definition is required")
    existing, _ = request("GET", args.billing_profile + "/billingRoleAssignments", "2024-04-01")
    current = [r for r in existing["value"]
               if r.get("properties",{}).get("principalId") == principal
               and r["properties"].get("roleDefinitionId") == readers[0]["id"]]
    if current:
        billing, billing_headers = current[0], {}
    else:
        billing, billing_headers = request("POST", args.billing_profile
            + "/createBillingRoleAssignment", "2024-04-01", {
                "principalId":principal,"principalTenantId":tenant,
                "roleDefinitionId":readers[0]["id"],"scope":args.billing_profile
            })
    state = {"identityResourceId":account,"principalId":principal,"tenantId":tenant,
             "labScope":lab,"vmRoleDefinitionId":role["id"],"vmRoleAssignmentId":assignment["id"],
             "billingProfileId":args.billing_profile,"billingAssignment":billing,
             "billingOperationLocation":billing_headers.get("Location")}
    destination = Path("/tmp/aegislake-identity-state.json")
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as out:
        json.dump(state, out, indent=2)
    print("Identity and grants submitted; verifying the live identity is a separate step.", flush=True)


if __name__ == "__main__":
    main()
