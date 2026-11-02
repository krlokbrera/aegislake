import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).parents[1]
for name in ["lab_budget_policy", "deploy_lab_guard"]:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
guard = sys.modules["deploy_lab_guard"]

SUB = "/subscriptions/11111111-1111-1111-1111-111111111111"
LAB = SUB + "/resourceGroups/rg-aegislake-lab"
IDENTITY = SUB + "/resourceGroups/rg-aegislake-control/providers/Microsoft.ManagedIdentity/userAssignedIdentities/test"
PROFILE = "/providers/Microsoft.Billing/billingAccounts/example/billingProfiles/example"


def actions_in(container):
    for name, action in container.items():
        yield name, action
        yield from actions_in(action.get("actions", {}))
        yield from actions_in(action.get("else", {}).get("actions", {}))


class GuardWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.workflow = guard.build_workflow(
            IDENTITY, PROFILE, LAB, 46.96, "2026-11-09T12:00:00Z"
        )

    def test_every_write_is_one_of_two_lab_deallocations(self):
        writes = [a for _, a in actions_in(self.workflow["actions"])
                  if a.get("type") == "Http" and a["inputs"]["method"] != "GET"]
        expected = {
            "https://management.azure.com" + LAB
            + "/providers/Microsoft.Compute/virtualMachines/" + name
            + "/deallocate?api-version=2024-07-01"
            for name in ["aegis-endpoint", "aegis-wazuh"]
        }
        self.assertEqual(len(writes), 4)
        self.assertEqual({a["inputs"]["uri"] for a in writes}, expected)
        self.assertEqual({a["inputs"]["method"] for a in writes}, {"POST"})

    def test_all_http_actions_use_the_approved_identity_without_secrets(self):
        for _, action in actions_in(self.workflow["actions"]):
            if action.get("type") == "Http":
                self.assertEqual(action["inputs"]["authentication"]["type"], "ManagedServiceIdentity")
                self.assertEqual(action["inputs"]["authentication"]["identity"], IDENTITY)
                self.assertNotIn("headers", action["inputs"])
        self.assertNotIn("Bearer ", json.dumps(self.workflow))

    def test_unreadable_credit_stops_and_failed_read_is_not_ignored(self):
        fallback = self.workflow["actions"]["StopOnUnreadableCredit"]
        self.assertEqual(set(fallback["runAfter"]["ValidateCredit"]), {"Failed", "Skipped", "TimedOut"})
        self.assertEqual(len(fallback["actions"]), 2)
        validator = self.workflow["actions"]["ValidateCredit"]["inputs"]["schema"]
        amount = validator["properties"]["properties"]["properties"]["balanceSummary"][
            "properties"]["estimatedBalanceInBillingCurrency"]
        self.assertEqual(amount["properties"]["currency"]["enum"], ["EUR"])
        self.assertEqual(amount["properties"]["value"]["minimum"], 0)

    def test_a_different_resource_group_is_rejected(self):
        with self.assertRaises(ValueError):
            guard.build_workflow(IDENTITY, PROFILE, SUB + "/resourceGroups/production", 46.96, "2026-11-09")

    def test_hard_deadline_and_manual_stop_drill_are_present(self):
        expression = self.workflow["actions"]["ApplyCreditPolicy"]["expression"]
        self.assertIn("parameters('DeadlineUtc')", expression)
        self.assertIn("parameters('ForceStop')", expression)
        self.assertFalse(self.workflow["parameters"]["ForceStop"]["defaultValue"])
        self.assertEqual(self.workflow["triggers"]["Hourly"]["recurrence"]["interval"], 1)


if __name__ == "__main__":
    unittest.main()
