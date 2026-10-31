"""ATT&CK mapping semantics and DeTT&CT YAML interoperability."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from aegislake.attack import describe_mapping, dettect_administration, write_attack_exports, yaml_text


class AttackTests(unittest.TestCase):
    def test_candidate_tactics_are_deduplicated_catalog_memberships(self):
        mapped = describe_mapping(["T1078", "T1078", "T1110.003"])
        self.assertEqual(mapped["status"], "hypothesis")
        self.assertEqual(len(mapped["techniques"]), 2)
        valid = next(item for item in mapped["techniques"] if item["technique_id"] == "T1078")
        self.assertEqual({item["tactic_id"] for item in valid["candidate_tactics"]},
                         {"TA0001", "TA0003", "TA0004", "TA0005"})
        self.assertNotIn("TA0008", str(valid))
        spray = next(item for item in mapped["techniques"] if item["technique_id"] == "T1110.003")
        self.assertEqual(spray["candidate_tactics"], [{"tactic_id": "TA0006", "tactic_name": "Credential Access"}])

    def test_unknown_ids_are_preserved_without_invented_tactics(self):
        mapped = describe_mapping(["T9999", "T9999"])
        self.assertEqual(mapped["techniques"], [])
        self.assertEqual(mapped["unmapped_technique_ids"], ["T9999"])
        self.assertEqual(describe_mapping([])["techniques"], [])

    def test_deployment_template_does_not_invent_operational_scores(self):
        template = dettect_administration()
        self.assertEqual(template["version"], 1.2)
        self.assertEqual(template["file_type"], "technique-administration")
        self.assertEqual(template["domain"], "enterprise-attack")
        for technique in template["techniques"]:
            detection, visibility = technique["detection"][0], technique["visibility"][0]
            self.assertEqual(detection["location"], [])
            self.assertEqual(detection["score_logbook"][0]["score"], -1)
            self.assertEqual(visibility["score_logbook"][0]["score"], 0)
            self.assertIsNone(detection["score_logbook"][0]["date"])
            self.assertFalse(visibility["score_logbook"][0]["auto_generated"])
            self.assertIn("Unassessed SOC", detection["applicable_to"][0])

    def test_yaml_loads_as_the_expected_administration_structure(self):
        template = dettect_administration()
        self.assertEqual(yaml.safe_load(yaml_text(template)), template)
        special = {"notes": "quotes: \"ok\"\nUnicode: áé and # comments", "flags": [True, None, 0], "empty": []}
        self.assertEqual(yaml.safe_load(yaml_text(special)), special)

    def test_export_counts_unique_windows_and_keeps_mapping_provenance(self):
        report = {"run_id": "test-run", "data_notice": "SYNTHETIC"}
        alerts = [{"alert_id": "a1", "user": "do-not-export-this-user", "source": "private-source",
                   "attack_hypotheses": ["T1078", "T1078", "T1110.003"]},
                  {"alert_id": "a2", "attack_hypotheses": []}]
        before = copy.deepcopy(alerts)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_attack_exports(root, report, alerts)
            text = (root / "attack-mapping.json").read_text(encoding="utf-8")
            exported = json.loads(text)
            self.assertEqual(exported["technique_counts"], {"T1078": 1, "T1110.003": 1})
            self.assertEqual(len(exported["alerts"]), 2)
            self.assertEqual(exported["alerts"][0]["alert_id"], "a1")
            self.assertNotIn("do-not-export-this-user", text)
            self.assertNotIn("private-source", text)
            self.assertEqual(yaml.safe_load((root / "dettect-techniques.yaml").read_text()),
                             dettect_administration())
        self.assertEqual(alerts, before)

    def test_empty_export_still_offers_a_reviewable_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_attack_exports(root, {"run_id": "empty", "data_notice": "SYNTHETIC"}, [])
            exported = json.loads((root / "attack-mapping.json").read_text())
            self.assertEqual(exported["technique_counts"], {"T1110.003": 0, "T1078": 0})
            self.assertEqual(exported["alerts"], [])


if __name__ == "__main__":
    unittest.main()
