import json

import pytest

from aegislake.contracts import canonical_event
from aegislake.lake import ingest


@pytest.mark.parametrize("patch", [
    {"timestamp": "2026-01-01T00:00:00"},
    {"timestamp": "not-a-date"},
    {"success": "false"},
    {"mfa": 1},
    {"label": True},
    {"label": 2},
    {"user": ""},
    {"source": "x" * 201},
    {"unexpected": "field"},
])
def test_invalid_events_are_rejected(event, patch):
    with pytest.raises(ValueError):
        canonical_event(event | patch)


def test_timezone_normalization_and_unknown_mfa(event):
    result = canonical_event(event | {"timestamp": "2026-01-05T11:01:00+01:00", "mfa": None})
    assert result["timestamp"] == "2026-01-05T10:01:00+00:00"
    assert result["mfa"] is None


def test_dispositions_reconcile_and_conflicts_quarantine(event, write_events, tmp_path):
    source = write_events([event, event, event | {"destination": "different"}, {"bad": "record"}])
    frame, quality = ingest(source, tmp_path / "run")
    assert len(frame) == 1
    assert quality == {"input_lines": 4, "accepted": 1, "duplicates": 1, "rejected": 2}
    rejected = json.loads((tmp_path / "run/quarantine/rejected.json").read_text())
    assert "alice" not in json.dumps(rejected)
    assert (tmp_path / "run/silver/event_date=2026-01-05/events.parquet").exists()


def test_empty_valid_input_fails(write_events, tmp_path):
    with pytest.raises(ValueError, match="no valid events"):
        ingest(write_events([{"bad": "record"}]), tmp_path / "run")


def test_source_is_snapshotted(event, write_events, tmp_path):
    source = write_events([event])
    original = source.read_bytes()
    ingest(source, tmp_path / "run")
    source.write_text("changed", encoding="utf-8")
    assert (tmp_path / "run/bronze/events.jsonl").read_bytes() == original
