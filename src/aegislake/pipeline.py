"""Reproducible immutable batch orchestration."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

from aegislake import __version__
from aegislake.evaluation import metrics, population_stability_index, queue_mask, select_threshold
from aegislake.features import FEATURES, temporal_partitions
from aegislake.lake import file_sha256, ingest, write_json
from aegislake.models import Models, explain
from aegislake.report import render_report
from aegislake.review import alert_id


def run(
    source: Path, output: Path, *, train_days: int = 18, validation_days: int = 6,
    capacity: int = 25, seed: int = 42, synthetic: bool = False,
) -> Path:
    if capacity < 1:
        raise ValueError("capacity must be positive")
    config = {"train_days": train_days, "validation_days": validation_days,
              "capacity": capacity, "seed": seed, "synthetic": synthetic, "version": __version__}
    input_hash = file_sha256(source)
    identifier = hashlib.sha256((input_hash + json.dumps(config, sort_keys=True)).encode()).hexdigest()[:20]
    final = output / identifier
    if final.exists():
        from aegislake.scoring import verify_run

        manifest = verify_run(final)
        if manifest["input_sha256"] != input_hash:
            raise ValueError("run manifest mismatch")
        return final
    output.mkdir(parents=True, exist_ok=True)
    staging = output / (identifier + ".partial")
    # Fail on overlapping run instead of concurrent writes or clobbering a failed checkpoint.
    staging.mkdir(exist_ok=False)
    try:
        events, quality = ingest(source, staging)
        if file_sha256(staging / "bronze" / "events.jsonl") != input_hash:
            raise ValueError("source changed during snapshot")
        train, validation, test = temporal_partitions(events, train_days, validation_days)
        if any(part["label"].isna().any() for part in (train, validation, test)):
            raise ValueError("benchmark pipeline requires labeled data; unlabelled production scoring is future work")
        models = Models.fit(train, seed)
        validation_scores = models.score(validation)
        test_scores = models.score(test)
        validation_results, test_results = {}, {}
        for name, scores in validation_scores.items():
            threshold = select_threshold(validation, scores, capacity)
            validation_results[name] = metrics(validation, scores, threshold, capacity)
            test_results[name] = metrics(test, test_scores[name], threshold, capacity)
        champion = max(validation_results, key=lambda name: (
            validation_results[name]["f1"], validation_results[name]["precision"], name
        ))
        threshold = validation_results[champion]["threshold"]
        scores = test_scores[champion]
        selected = queue_mask(test, scores, threshold, capacity)
        alerts = []
        for position, (_, row) in enumerate(test.iterrows()):
            if not selected[position]:
                continue
            user, stamp = str(row["user"]), row["window_start"].isoformat()
            alerts.append({
                "alert_id": alert_id(user, stamp), "user": user, "window_start": stamp,
                "window_end": row["window_end"].isoformat(), "score": float(scores[position]),
                "model": champion, **explain(row),
            })
        alerts.sort(key=lambda item: (item["window_start"][:10], -item["score"], item["alert_id"]))
        gold = staging / "gold"
        gold.mkdir()
        for name, frame in (("train", train), ("validation", validation), ("test", test)):
            frame.to_parquet(gold / f"{name}_features.parquet", index=False)
        write_json(gold / "alerts.json", alerts)
        drift = {name: population_stability_index(train[name].to_numpy(), test[name].to_numpy()) for name in FEATURES}
        report = {
            "run_id": identifier, "champion": champion, "capacity": capacity,
            "validation": validation_results, "test": test_results, "feature_drift_diagnostics": drift,
            "quality": quality, "config": config, "features": FEATURES,
            "data_notice": (
                "SYNTHETIC DEMONSTRATION. Results measure a simulator and do not establish real-world detection."
                if synthetic else
                "LABELED OFFLINE DATA. Labels and collection scope limit generalization; review the data card."
            ),
            "split_boundaries": {
                "train_last_window_end": train["window_end"].max().isoformat(),
                "validation_first_window": validation["window_start"].min().isoformat(),
                "validation_last_window_end": validation["window_end"].max().isoformat(),
                "test_first_window": test["window_start"].min().isoformat(),
            },
        }
        render_report(staging, report, alerts)
        manifest = {
            "run_id": identifier, "input_sha256": input_hash, "config": config,
            "created_at": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
            "packages": {name: importlib.metadata.version(name) for name in
                         ("duckdb", "numpy", "pandas", "pyarrow", "scikit-learn")},
            "artifacts": {
                path.relative_to(staging).as_posix(): file_sha256(path)
                for path in sorted(staging.rglob("*")) if path.is_file()
            },
        }
        write_json(staging / "manifest.json", manifest)
        staging.rename(final)
    except Exception:
        # Preserve failed staging for diagnosis. Never publish a partial run as successful.
        raise
    return final

