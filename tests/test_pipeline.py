import json

import pandas as pd
import pytest

from aegislake.azure import publish
from aegislake.pipeline import run
from aegislake.scoring import score, verify_run


def test_end_to_end_manifest_splits_and_idempotency(completed_run):
    source, path = completed_run
    manifest = verify_run(path)
    assert {"mitre.html", "dashboard.html", "dashboard.json", "attack-mapping.json",
            "dettect-techniques.yaml"} <= manifest["artifacts"].keys()
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
    dashboard = json.loads((destination / "dashboard.json").read_text())
    assert dashboard["run"]["data_kind"] == "unlabeled"
    assert dashboard["run"]["benchmark"] is None
    assert (destination / "dashboard.html").is_file()


@pytest.mark.parametrize("fail_yaml", [False, True])
def test_cloud_publication_keeps_linked_exports_and_commits_last(completed_run, monkeypatch, fail_yaml):
    import sys
    from types import ModuleType, SimpleNamespace

    from aegislake.azure import PUBLISH_FILES

    _, path = completed_run
    uploads = []
    closed = []

    class Credential:
        def close(self):
            closed.append(True)

    class Blob:
        def __init__(self, name):
            self.name = name

        def upload_blob(self, payload, *, overwrite, content_settings):
            if fail_yaml and self.name.endswith(".yaml"):
                raise RuntimeError("simulated upload failure")
            data = payload.read() if hasattr(payload, "read") else payload
            uploads.append((self.name, data, content_settings.content_type))

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get_blob_client(self, container, name):
            return Blob(name)

    # Exercise the SDK protocol without requiring optional cloud packages or credentials locally.
    modules = {name: ModuleType(name) for name in ("azure", "azure.identity", "azure.storage", "azure.storage.blob")}
    modules["azure.identity"].DefaultAzureCredential = lambda **kwargs: Credential()
    modules["azure.storage.blob"].BlobServiceClient = Client
    modules["azure.storage.blob"].ContentSettings = lambda **kwargs: SimpleNamespace(**kwargs)
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)
    if fail_yaml:
        with pytest.raises(RuntimeError, match="simulated"):
            publish(path, "aegisexample")
        assert not any(name.endswith("publication.json") for name, _, _ in uploads)
    else:
        published = publish(path, "aegisexample")
        assert len(published) == len(PUBLISH_FILES)
        assert uploads[-1][0].endswith("publication.json")
        assert json.loads(uploads[-1][1])["files"] == published
        assert any(name.endswith("mitre.html") and mime == "text/html" for name, _, mime in uploads)
        assert any(name.endswith("dettect-techniques.yaml") and mime == "application/yaml"
                   for name, _, mime in uploads)
        assert any(name.endswith("attack-mapping.json") and mime == "application/json"
                   for name, _, mime in uploads)
    assert closed == [True]
