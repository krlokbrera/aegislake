"""Atomic per-run bronze/silver lake, duplicate handling, and quarantine accounting."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pandas as pd

from aegislake.contracts import canonical_event, content_digest


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
    os.replace(temporary, path)


def ingest(source: Path, run_dir: Path) -> tuple[pd.DataFrame, dict]:
    """Snapshot source before processing. Every line has exactly one disposition."""
    bronze = run_dir / "bronze"
    bronze.mkdir(parents=True, exist_ok=True)
    snapshot = bronze / "events.jsonl"
    # Stream snapshot to bound copy memory; parser itself is single-node and in-memory.
    with source.open("rb") as incoming, snapshot.open("xb") as outgoing:
        for block in iter(lambda: incoming.read(1024 * 1024), b""):
            outgoing.write(block)
    rows: list[dict] = []
    seen: dict[str, str] = {}
    quarantine: list[dict] = []
    quality = {"input_lines": 0, "accepted": 0, "duplicates": 0, "rejected": 0}
    with snapshot.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            quality["input_lines"] += 1
            try:
                event = canonical_event(json.loads(line))
                fingerprint = content_digest(event)
                if event["event_id"] in seen:
                    if seen[event["event_id"]] == fingerprint:
                        quality["duplicates"] += 1
                        continue
                    raise ValueError("conflicting duplicate event_id")
                seen[event["event_id"]] = fingerprint
                rows.append(event)
                quality["accepted"] += 1
            except (ValueError, TypeError) as exc:
                quality["rejected"] += 1
                # Do not copy raw records or identifier values into the quality log.
                quarantine.append({"line_number": line_number, "reason": str(exc)[:180]})
    write_json(run_dir / "quarantine" / "rejected.json", quarantine)
    write_json(run_dir / "quality.json", quality)
    if not rows:
        raise ValueError("no valid events")
    frame = pd.DataFrame(rows)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame = frame.sort_values(["timestamp", "event_id"]).reset_index(drop=True)
    silver = run_dir / "silver"
    silver.mkdir()
    for date, partition in frame.groupby(frame["timestamp"].dt.strftime("%Y-%m-%d")):
        folder = silver / f"event_date={date}"
        folder.mkdir()
        partition.to_parquet(folder / "events.parquet", index=False)
    assert sum(quality[key] for key in ("accepted", "duplicates", "rejected")) == quality["input_lines"]
    return frame, quality
