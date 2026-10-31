"""Behavioral regression checks for offline report rendering."""

import copy
import json
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from aegislake.report import daily_chart, render_report


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.elements = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        value = {"average_precision": .8, "precision": .75, "recall": .6, "f1": .66,
                 "alerts": 2, "confusion_matrix": {"tp": 1, "fp": 1, "fn": 1, "tn": 10}}
        self.report = {
            "run_id": "example-run", "champion": "rules", "capacity": 5,
            "test": {"rules": value}, "quality": {"input_lines": 12, "accepted": 10,
                                                 "duplicates": 1, "rejected": 1},
            "config": {"synthetic": True},
            "data_notice": "SYNTHETIC DEMONSTRATION.",
            "split_boundaries": {"test_first_window": "2026-01-01T00:00:00+00:00",
                                 "test_last_window_end": "2026-01-03T23:45:00+00:00"},
        }
        self.alerts = [
            {"user": "employee-1", "alert_id": "a1", "window_start": "2026-01-01T10:00:00+00:00",
             "score": .9, "reasons": ["Observed fanout"], "next_steps": ["Check approved changes"],
             "attack_hypotheses": ["T1078", "T1078", "T1110.003"]},
            {"user": "employee-2", "alert_id": "a2", "window_start": "2026-01-02T10:00:00+00:00",
             "score": .8, "reasons": [], "attack_hypotheses": []},
        ]

    def tearDown(self):
        self.temp.cleanup()

    def render(self):
        render_report(self.root, self.report, self.alerts)
        return ((self.root / "report.html").read_text(encoding="utf-8"),
                (self.root / "mitre.html").read_text(encoding="utf-8"))

    def test_two_offline_pages_and_roundtrip_metrics(self):
        overview, mitre = self.render()
        self.assertEqual(json.loads((self.root / "report.json").read_text()), self.report)
        for text in (overview, mitre):
            doc = Document(text)
            self.assertFalse(any(tag in ("img", "iframe", "link") for tag, _ in doc.elements))
            self.assertFalse(any(tag == "script" and "src" in attrs for tag, attrs in doc.elements))
            self.assertIn("default-src 'none'", text)
            self.assertIn("Skip to content", text)
        self.assertTrue(any(tag == "a" and attrs.get("href") == "mitre.html"
                            for tag, attrs in Document(overview).elements))
        self.assertIn("report.html?technique=T1078#queue", mitre)

    def test_untrusted_strings_cannot_create_markup_or_event_attributes(self):
        payload = '\"><img src=x onerror=alert(1)></script><script>alert(2)</script>'
        self.alerts[0].update(user=payload, alert_id=payload, reasons=[payload],
                              attack_hypotheses=[payload])
        self.report["data_notice"] = payload
        self.report["run_id"] = payload
        overview, mitre = self.render()
        for text in (overview, mitre):
            self.assertNotIn("<img", text)
            self.assertEqual(sum(tag == "script" for tag, _ in Document(text).elements), 1)
            self.assertFalse(any(key.startswith("on") for _, attrs in Document(text).elements
                                 for key in attrs))
        row = next(attrs for _, attrs in Document(overview).elements if "data-alert" in attrs)
        self.assertEqual(row["data-user"], payload)
        self.assertEqual(row["data-alert-id"], payload)

    def test_zero_alert_days_are_explicit(self):
        text = daily_chart(self.report, self.alerts)
        self.assertIn("2026-01-01: 1 alerts", text)
        self.assertIn("2026-01-02: 1 alerts", text)
        self.assertIn("2026-01-03: 0 alerts", text)

    def test_mapping_counts_deduplicate_per_alert_and_preserve_unmapped(self):
        _, text = self.render()
        # One mapped alert with duplicate T1078 entries must still count once.
        self.assertIn("<span>Mapped alert windows</span><strong>1</strong>", text)
        self.assertIn("<span>Observed techniques</span><strong>2</strong>", text)
        self.assertIn("<span>Without a supported mapping</span><strong>1</strong>", text)
        self.assertEqual(text.count('data-technique="T1078"'), 4)
        self.assertIn("counts overlap and must not be added", text)
        self.assertIn("does not measure ATT&amp;CK detection coverage", text)

    def test_empty_queue_and_no_positive_labels(self):
        self.alerts = []
        self.report["split_boundaries"] = {}
        self.report["test"]["rules"].update(average_precision=None, precision=0, recall=0, alerts=0,
                                            confusion_matrix={"tp": 0, "fp": 0, "tn": 10, "fn": 0})
        overview, text = self.render()
        self.assertIn("No queued alerts", overview)
        self.assertIn("No queued windows to evaluate", overview)
        self.assertIn("N/A", overview)
        self.assertIn("<span>Observed techniques</span><strong>0</strong>", text)

    def test_unknown_techniques_are_text_not_links(self):
        self.alerts[0]["attack_hypotheses"] = ["javascript:alert(1)"]
        overview, text = self.render()
        self.assertFalse(any(attrs.get("href", "").startswith("javascript:")
                             for _, attrs in Document(overview).elements))
        self.assertIn("<span>Mapped alert windows</span><strong>0</strong>", text)

    def test_alert_data_supports_id_search_and_exact_technique_filters(self):
        overview, _ = self.render()
        rows = [attrs for _, attrs in Document(overview).elements if "data-alert" in attrs]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["data-alert-id"], "a1")
        self.assertEqual(rows[0]["data-techniques"], "T1078 T1110.003")
        self.assertEqual(float(rows[1]["data-score"]), .8)

    def test_rendering_does_not_mutate_metrics_or_alerts(self):
        before = copy.deepcopy((self.report, self.alerts))
        self.render()
        self.assertEqual(before, (self.report, self.alerts))

    def test_incomplete_legacy_report_keeps_evidence_without_fabricated_metrics(self):
        self.report = {"champion": "unavailable-model", "capacity": 5, "run_id": "legacy",
                       "test": {}, "data_notice": "Offline incomplete report"}
        overview, _ = self.render()
        self.assertIn("Incomplete evaluation", overview)
        self.assertIn("Selected-model metrics are unavailable", overview)
        self.assertIn("employee-1", overview)
        self.assertNotIn("Test precision", overview)


if __name__ == "__main__":
    unittest.main()
