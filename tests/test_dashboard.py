"""Dashboard contracts, hostile-input handling and real HTTP isolation checks."""

import copy
import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

from aegislake.dashboard import dashboard_page, normalize_alerts, read_snapshot, snapshot, write_dashboard
from aegislake.dashboard_server import catalog, create_server, navigation


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.report = {"run_id": "demo-test", "champion": "rules", "capacity": 25,
                       "config": {"synthetic": True}, "data_notice": "SYNTHETIC DEMONSTRATION",
                       "test": {"rules": {"precision": .8, "recall": .7, "average_precision": .9, "f1": .75}}}
        self.alerts = [{"alert_id": "a1", "user": "employee-1", "window_start": "2026-01-01T01:00:00+01:00",
                        "score": .9, "attack_hypotheses": ["T1078", "T1078"], "reasons": ["Observed fanout"],
                        "private_source": "must-not-be-exported"}]

    def tearDown(self):
        self.temp.cleanup()

    def test_snapshot_uses_utc_deduplicates_and_excludes_arbitrary_fields(self):
        original = copy.deepcopy(self.alerts)
        data = snapshot(self.report, self.alerts)
        self.assertEqual(data["alerts"][0]["window_start"], "2026-01-01T00:00:00+00:00")
        self.assertEqual(data["alerts"][0]["attack_hypotheses"], ["T1078"])
        self.assertNotIn("private_source", json.dumps(data))
        self.assertEqual(original, self.alerts)
        self.assertEqual(len(data["techniques"]["T1078"]["candidate_tactics"]), 4)

    def test_scoring_never_inherits_reference_benchmark_or_synthetic_data_claim(self):
        data = snapshot(self.report, self.alerts, kind="scoring")
        self.assertIsNone(data["run"]["benchmark"])
        self.assertEqual(data["run"]["data_kind"], "unlabeled")

    def test_invalid_scores_naive_dates_and_duplicate_ids_are_rejected(self):
        for update in ({"score": float("nan")}, {"score": float("inf")}, {"score": True},
                       {"score": 1.01}, {"score": -.1}, {"window_start": "2026-01-01T00:00:00"},
                       {"window_start": "not-a-date"}, {"attack_hypotheses": "T1078"}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                normalize_alerts([{**self.alerts[0], **update}])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            normalize_alerts(self.alerts * 2)

    def test_empty_scoring_batch_has_no_fabricated_metrics(self):
        data = snapshot(self.report, [], kind="scoring")
        self.assertEqual(data["alerts"], [])
        self.assertIsNone(data["run"]["benchmark"])

    def test_embedded_json_cannot_break_script_boundary(self):
        self.alerts[0]["user"] = '</script><script>alert("private")</script>'
        page = dashboard_page(snapshot(self.report, self.alerts))
        self.assertNotIn(self.alerts[0]["user"], page)
        self.assertIn("\\u003c/script>", page)
        self.assertNotIn("<iframe", page)
        self.assertNotIn("<script src=", page)
        self.assertNotIn("connect-src", page)
        self.assertIn("connect-src &#39;self&#39;", dashboard_page(api=True))

    def test_snapshot_roundtrip_and_unknown_schema(self):
        write_dashboard(self.root, self.report, self.alerts)
        self.assertEqual(read_snapshot(self.root / "dashboard.json"), snapshot(self.report, self.alerts))
        (self.root / "dashboard.json").write_text('{"schema":"unknown"}')
        with self.assertRaisesRegex(ValueError, "schema"):
            read_snapshot(self.root / "dashboard.json")

    def test_unlabeled_import_cannot_claim_evaluation_metrics(self):
        write_dashboard(self.root, self.report, self.alerts, kind="scoring")
        value = json.loads((self.root / "dashboard.json").read_text())
        value["run"]["benchmark"] = {"precision": .99}
        (self.root / "dashboard.json").write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "effectiveness"):
            read_snapshot(self.root / "dashboard.json")

    def test_catalog_requires_completion_and_ignores_partial_and_malformed_batches(self):
        for name in ("complete", "pending", "bad", "unfinished.partial"):
            directory = self.root / name
            directory.mkdir()
            write_dashboard(directory, self.report, self.alerts)
            if name != "pending":
                (directory / "manifest.json").write_text("{}")
        (self.root / "bad/dashboard.json").write_text("broken")
        entries = catalog(self.root)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["path"].name, "complete")

    def test_navigation_preserves_filters_and_fragments_inside_selected_run(self):
        output = navigation('<a href="report.html?technique=T1078#queue">Alerts</a>'
                            '<a href="mitre.html#T1078">Map</a><a href="https://example.org">Ref</a>', "abc")
        self.assertIn('report.html?technique=T1078&amp;run=abc#queue', output)
        self.assertIn('mitre.html?run=abc#T1078', output)
        self.assertIn('href="https://example.org"', output)


class DashboardHTTPTests(unittest.TestCase):
    def setUp(self):
        DashboardTests.setUp(self)
        directory = self.root / "batch"
        directory.mkdir()
        write_dashboard(directory, self.report, self.alerts)
        (directory / "manifest.json").write_text("{}")
        (directory / "report.html").write_text('<a href="mitre.html#T1078">Map</a>')
        self.server = create_server(self.root, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        DashboardTests.tearDown(self)

    def request(self, path, headers=None):
        conn = HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        try:
            conn.request("GET", path, headers=headers or {})
            response = conn.getresponse()
            return response.status, dict(response.headers), response.read()
        finally:
            conn.close()

    def test_real_http_catalog_snapshot_and_html_navigation(self):
        status, headers, body = self.request("/api/runs")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Cache-Control"], "no-store")
        entry = json.loads(body)["runs"][0]
        self.assertNotIn("path", entry)
        status, _, body = self.request(f'/api/runs/{entry["key"]}/dashboard')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["alerts"][0]["alert_id"], "a1")
        status, _, body = self.request('/report.html?run=' + entry["key"])
        self.assertEqual(status, 200)
        self.assertIn(('?run=' + entry["key"] + '#T1078').encode(), body)

    def test_completed_new_batch_is_discovered_without_restart(self):
        before = json.loads(self.request("/api/runs")[2])["runs"]
        directory = self.root / "second"
        directory.mkdir()
        write_dashboard(directory, {**self.report, "run_id": "new-batch"}, [])
        self.assertEqual(len(json.loads(self.request("/api/runs")[2])["runs"]), len(before))
        (directory / "scoring.json").write_text("{}")
        self.assertEqual(len(json.loads(self.request("/api/runs")[2])["runs"]), len(before) + 1)

    def test_traversal_private_files_unknown_runs_and_foreign_origins_are_rejected(self):
        for path in ("/../manifest.json", "/%2e%2e/manifest.json", "/gold/alerts.json", "/api/runs/../../x/dashboard",
                     "/report.html?run=unknown"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)
        self.assertEqual(self.request("/api/runs", {"Host": "attacker.example"})[0], 403)
        self.assertEqual(self.request("/api/runs", {"Origin": "https://attacker.example"})[0], 403)
        self.assertEqual(self.request("/api/runs", {"Origin": "null"})[0], 403)


if __name__ == "__main__":
    unittest.main()
