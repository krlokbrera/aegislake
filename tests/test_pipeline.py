import json

import pandas as pd
import pytest

from aegislake.azure import publish
from aegislake.pipeline import run
from aegislake.scoring import score, verify_run


def test_end_to_end_manifest_splits_and_idempotency(completed_run):
    source, path = completed_run
    manifest = verify_run(path)
    report = json.loads((path / "report.json").read_text())
    assert report["quality"]["duplicates"] == 1
    assert report["quality"]["rejected"] == 1
    assert "SYNTHETIC" in report["data_notice"]
    train = pd.read_parquet(path / "gold/train_features.parquet")
    validation = pd.read_parquet(path / "gold/validation_features.parquet")
    test = pd.read_parquet(path / "gold/test_features.parquet")
    assert train["window_end"].max() <= validation["window_start"].min()
    assert validation["window_end"].max() <= test["window_start"].min()
    for result in report["test"].values():
        assert result["daily_alerts_max"] <= 12
    assert run(source, path.parent, **{key: manifest["config"][key] for key in
               ("train_days", "validation_days", "capacity", "seed", "synthetic")}) == path


def test_tampered_artifact_is_rejected(completed_run, tmp_path):
    import shutil

    _, path = completed_run
    copy = tmp_path / "copy"
    shutil.copytree(path, copy)
    (copy / "quality.json").write_text("{}")
    with pytest.raises(ValueError, match="integrity"):
        verify_run(copy)


def test_cloud_destination_and_real_data_publication_guard(completed_run, tmp_path):
    import shutil

    _, path = completed_run
    with pytest.raises(ValueError, match="account"):
        publish(path, "https://evil.example")
    copy = tmp_path / "real"
    shutil.copytree(path, copy)
    manifest = json.loads((copy / "manifest.json").read_text())
    manifest["config"]["synthetic"] = False
    (copy / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="only synthetic"):
        publish(copy, "aegisexample")


def test_unlabeled_future_scoring_has_no_evaluation_metrics(completed_run, event, tmp_path):
    _, reference = completed_run
    source = tmp_path / "future.jsonl"
    source.write_text(json.dumps(event | {
        "timestamp": "2026-02-10T10:01:00Z", "label": None,
    }) + "\n")
    with pytest.raises(ValueError, match="domain-shift"):
        score(reference, source, tmp_path / "refused")
    destination = score(reference, source, tmp_path / "scored", allow_domain_shift=True)
    result = json.loads((destination / "scoring.json").read_text())
    assert result["windows"] == 1
    assert result["metrics"] is None
