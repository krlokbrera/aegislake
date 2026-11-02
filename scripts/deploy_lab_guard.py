"""Build a fail-closed, identity-authenticated Azure Logic Apps credit guard.

The operator supplies verified regional cost allowances. This module never
creates roles or VMs. Only the two named lab VMs can be deallocated.
"""
from datetime import datetime, timedelta, timezone
import argparse
import json
from pathlib import Path
import subprocess
import urllib.request
import urllib.error

from lab_budget_policy import decide


def build_workflow(identity_id, billing_profile, lab_scope, threshold, deadline, force_stop=False):
    if not lab_scope.endswith("/resourceGroups/rg-aegislake-lab"):
        raise ValueError("Only the dedicated lab group is supported")
    if not identity_id.startswith("/subscriptions/") or "/userAssignedIdentities/" not in identity_id:
        raise ValueError("Expected a user-assigned identity")
    if not billing_profile.startswith("/providers/Microsoft.Billing/billingAccounts/"):
        raise ValueError("Expected a billing profile ID")
    auth = {"type":"ManagedServiceIdentity","identity":identity_id,
            "audience":"https://management.azure.com/"}
    secure = {"secureData":{"properties":["inputs","outputs"]}}
    balance = {"type":"object","required":["currency","value"],
               "properties":{"currency":{"type":"string","enum":["EUR"]},
                             "value":{"type":"number","minimum":0}}}
    summary = {"type":"object","required":["estimatedBalanceInBillingCurrency"],
               "properties":{"estimatedBalanceInBillingCurrency":balance}}
    properties = {"type":"object","required":["billingCurrency","balanceSummary"],
                  "properties":{"billingCurrency":{"type":"string","enum":["EUR"]},
                                "balanceSummary":summary}}
    schema = {"type":"object","required":["properties"],"properties":{"properties":properties}}

    def stop_actions(prefix):
        result = {}
        for label, name in [("Endpoint","aegis-endpoint"),("Wazuh","aegis-wazuh")]:
            result[prefix+label] = {
                "type":"Http","runAfter":{},"operationOptions":"DisableAsyncPattern",
                "runtimeConfiguration":secure,
                "inputs":{"method":"POST",
                    "uri":"https://management.azure.com"+lab_scope
                        +"/providers/Microsoft.Compute/virtualMachines/"+name
                        +"/deallocate?api-version=2024-07-01",
                    "authentication":auth,
                    "retryPolicy":{"type":"fixed","count":3,"interval":"PT10S"}}
            }
        return result

    expression = (
        "@or(parameters('ForceStop'),"
        "greaterOrEquals(ticks(utcNow()),ticks(parameters('DeadlineUtc'))),"
        "lessOrEquals(float(body('ValidateCredit')?['properties']?['balanceSummary']"
        "?['estimatedBalanceInBillingCurrency']?['value']),parameters('StopThresholdEur')))"
    )
    return {
        "$schema":"https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
        "contentVersion":"1.0.0.0",
        "parameters":{
            "StopThresholdEur":{"type":"Float","defaultValue":float(threshold)},
            "DeadlineUtc":{"type":"String","defaultValue":deadline},
            "ForceStop":{"type":"Bool","defaultValue":force_stop},
        },
        "triggers":{"Hourly":{
            "type":"Recurrence",
            "recurrence":{"frequency":"Hour","interval":1,
                "startTime":(datetime.now(timezone.utc)+timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")},
            "runtimeConfiguration":{"concurrency":{"runs":1}},
        }},
        "actions":{
            "ReadCredit":{
                "type":"Http","runAfter":{},"runtimeConfiguration":secure,
                "inputs":{"method":"GET",
                    "uri":"https://management.azure.com"+billing_profile
                        +"/providers/Microsoft.Consumption/credits/balanceSummary?api-version=2023-05-01",
                    "authentication":auth,
                    "retryPolicy":{"type":"fixed","count":3,"interval":"PT10S"}},
            },
            "ValidateCredit":{
                "type":"ParseJson","runAfter":{"ReadCredit":["Succeeded"]},
                "runtimeConfiguration":{"secureData":{"properties":["inputs"]}},
                "inputs":{"content":"@body('ReadCredit')","schema":schema},
            },
            "ApplyCreditPolicy":{
                "type":"If","expression":expression,
                "runAfter":{"ValidateCredit":["Succeeded"]},
                "actions":stop_actions("BudgetStop"),
                "else":{"actions":{"WithinBudget":{
                    "type":"Compose","runAfter":{},
                    "inputs":{"creditReadable":True,"eurCredit":True,"stopRequired":False},
                }}},
            },
            "StopOnUnreadableCredit":{
                "type":"Scope",
                "runAfter":{"ValidateCredit":["Failed","Skipped","TimedOut"]},
                "actions":stop_actions("UnreadableStop"),
            },
        },
        "outputs":{},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity-state", required=True)
    parser.add_argument("--deadline-utc", required=True)
    parser.add_argument("--hourly-ceiling-eur", required=True)
    parser.add_argument("--residual-disk-eur", required=True)
    parser.add_argument("--force-stop", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    state = json.loads(Path(args.identity_state).read_text())
    deadline = datetime.fromisoformat(args.deadline_utc.replace("Z","+00:00"))
    if deadline.tzinfo is None or deadline <= datetime.now(timezone.utc):
        raise ValueError("Expected a future timezone-aware deadline")
    decision = decide({}, hourly_ceiling_eur=args.hourly_ceiling_eur,
        residual_disk_eur=args.residual_disk_eur, deadline_utc=deadline)
    definition = build_workflow(state["identityResourceId"],state["billingProfileId"],
        state["labScope"],decision.threshold_eur,args.deadline_utc,args.force_stop)
    if not args.apply:
        print(json.dumps(definition,indent=2))
        return
    token = subprocess.check_output(["az","account","get-access-token",
        "--query","accessToken","-o","tsv"],text=True).strip()
    identity = state["identityResourceId"]
    workflow = identity.split("/providers/")[0] + "/providers/Microsoft.Logic/workflows/la-aegislake-creditguard"
    body = {"location":"spaincentral",
        "identity":{"type":"UserAssigned","userAssignedIdentities":{identity:{}}},
        "tags":{"project":"aegislake","purpose":"credit-guard"},
        "properties":{"state":"Enabled","definition":definition,"parameters":{}}}
    req = urllib.request.Request("https://management.azure.com"+workflow+"?api-version=2019-05-01",
        data=json.dumps(body).encode(),method="PUT",
        headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=60) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(str(error.code) + " " + error.read().decode()) from None
    print(json.dumps({"workflow":result["name"],"state":result["properties"]["state"],
        "stopThresholdEur":float(decision.threshold_eur),"deadlineUtc":args.deadline_utc,
        "forceStop":args.force_stop}))


if __name__ == "__main__":
    main()
