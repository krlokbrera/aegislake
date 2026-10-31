import json
import sqlite3

import pytest

from aegislake.adapters import entra_event, pseudonym
from aegislake.report import render_report
from aegislake.review import record_review


def graph_event():
    return {
        "id": "graph-id", "createdDateTime": "2026-02-10T10:00:00Z", "userId": "private-user",
        "ipAddress": "198.51.100.10", "resourceId": "private-resource", "status": {"errorCode": 0},
        "location": {"countryOrRegion": "ES"}, "authenticationRequirement": "multiFactorAuthentication",
    }


def test_hmac_is_keyed_domain_separated_and_deterministic():
    key = b"x" * 32
    assert pseudonym("alice", key, "user") == pseudonym("alice", key, "user")
    assert pseudonym("alice", key, "user") != pseudonym("alice", b"y" * 32, "user")
    assert pseudonym("alice", key, "user") != pseudonym("alice", key, "source")
    with pytest.raises(ValueError):
        pseudonym("alice", b"short", "user")


def test_graph_policy_is_not_mfa_evidence():
    adapted = entra_event(graph_event(), b"x" * 32)
    assert adapted["mfa"] is None
    assert adapted["label"] is None
    assert "private-user" not in json.dumps(adapted)
    assert "198.51.100.10" not in json.dumps(adapted)


def test_actual_mfa_step_can_be_observed():
    raw = graph_event()
    raw["authenticationDetails"] = [{"authenticationStepRequirement": "multiFactorAuthentication", "succeeded": True}]
    assert entra_event(raw, b"x" * 32)["mfa"] is True


def test_review_ledger_is_append_only_at_application_level(tmp_path):
    (tmp_path / "gold").mkdir()
    (tmp_path / "gold/alerts.json").write_text(json.dumps([{"alert_id": "test-id"}]))
    record_review(tmp_path, "test-id", "needs_context", "analyst")
    record_review(tmp_path, "test-id", "false_positive", "analyst", "Approved maintenance")
    connection = sqlite3.connect(tmp_path / "reviews.sqlite")
    try:
        assert connection.execute("SELECT count(*) FROM reviews").fetchone()[0] == 2
    finally:
        connection.close()
    with pytest.raises(ValueError, match="unknown alert"):
        record_review(tmp_path, "absent", "true_positive", "analyst")


def test_report_escapes_untrusted_identifiers(tmp_path):
    payload = "<img src=x onerror=alert(1)>"
    report = {"champion": payload, "capacity": 1, "run_id": "test", "test": {}, "data_notice": "test"}
    alert = {"user": payload, "window_start": "2026-01-01T00:00:00Z", "score": 0.9,
             "alert_id": "test", "reasons": [payload], "attack_hypotheses": []}
    render_report(tmp_path, report, [alert])
    text = (tmp_path / "report.html").read_text()
    assert "<img src=x" not in text
    assert "&lt;img" in text
