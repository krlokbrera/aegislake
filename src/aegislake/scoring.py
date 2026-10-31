"""Unlabeled batch scoring from an integrity-checked reference; no pickle loading."""

from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path

import pandas as pd

from aegislake import __version__
from aegislake.evaluation import queue_mask
from aegislake.features import build_features
from aegislake.lake import file_sha256, ingest, write_json
from aegislake.models import Models, explain
from aegislake.review import alert_id


def verify_run(run_dir: Path) -> dict:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest["config"]["version"] != __version__:
        raise ValueError("reference code version differs")
    for relative, digest in manifest["artifacts"].items():
        path = (run_dir / relative).resolve()
        if not path.is_relative_to(run_dir.resolve()) or path.is_symlink():
            raise ValueError("invalid manifest path")
        if file_sha256(path) != digest:
            raise ValueError("reference integrity check failed")
    return manifest


def score(reference: Path, source: Path, destination: Path, *, allow_domain_shift: bool = False) -> Path:
    manifest = verify_run(reference)
    for package, expected in manifest["packages"].items():
        if importlib.metadata.version(package) != expected:
            raise ValueError("reference dependency versions differ; reproduce its environment first")
    report = json.loads((reference / "report.json").read_text(encoding="utf-8"))
    if manifest["config"]["synthetic"] and not allow_domain_shift:
        raise ValueError("synthetic-trained reference requires explicit --allow-domain-shift for new data")
    destination.mkdir(parents=True, exist_ok=False)
    events, quality = ingest(source, destination)
    test = pd.read_parquet(reference / "gold" / "test_features.parquet")
    if events["timestamp"].min() < test["window_end"].max():
        raise ValueError("new scoring data must start after the reference test period ends")
    train = pd.read_parquet(reference / "gold" / "train_features.parquet")
    train_end = pd.Timestamp(report["split_boundaries"]["train_last_window_end"])
    history = pd.read_parquet(reference / "silver")
    history = history.loc[history["timestamp"] < train_end]
    features = build_features(pd.concat([history, events], ignore_index=True), train_end)
    features = features.loc[features["window_start"] >= events["timestamp"].min().floor("15min")].copy()
    models = Models.fit(train, manifest["config"]["seed"])
    champion = report["champion"]
    scores = models.score(features)[champion]
    threshold = report["validation"][champion]["threshold"]
    selected = queue_mask(features, scores, threshold, report["capacity"])
    alerts = []
    for pos, (_, row) in enumerate(features.iterrows()):
        if selected[pos]:
            user, stamp = str(row["user"]), row["window_start"].isoformat()
            alerts.append({
                "alert_id": alert_id(user, stamp), "user": user, "window_start": stamp,
                "window_end": row["window_end"].isoformat(),
                "score": float(scores[pos]), "model": champion, **explain(row),
            })
    (destination / "gold").mkdir()
    features.to_parquet(destination / "gold" / "scored_features.parquet", index=False)
    write_json(destination / "gold" / "alerts.json", alerts)
    write_json(destination / "scoring.json", {
        "reference_run_id": manifest["run_id"], "input_sha256": file_sha256(source),
        "alerts": len(alerts), "windows": len(features), "quality": quality,
        "warning": "Experimental offline scoring. Domain shift requires separate validation.",
        "metrics": None, "synthetic_reference": manifest["config"]["synthetic"],
    })
    return destination
