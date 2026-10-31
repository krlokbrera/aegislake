import json

import pytest

from aegislake.pipeline import run
from aegislake.synthetic import generate


@pytest.fixture
def event():
    return {
        "event_id": "e-001", "timestamp": "2026-01-05T10:01:00+00:00",
        "user": "alice", "source": "device-1", "destination": "app-1",
        "success": True, "mfa": True, "country": "ES", "label": 0,
    }


@pytest.fixture(scope="session")
def completed_run(tmp_path_factory):
    root = tmp_path_factory.mktemp("reference")
    source = root / "input.jsonl"
    generate(source, days=15, users=12, seed=123)
    destination = run(
        source, root / "runs", train_days=9, validation_days=3, capacity=12, seed=123, synthetic=True
    )
    return source, destination


@pytest.fixture
def write_events(tmp_path):
    def write(rows):
        path = tmp_path / "input.jsonl"
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        return path
    return write
