"""Versioned dashboard snapshots shared by offline HTML and the local read-only API."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

from aegislake.attack import TECHNIQUES, describe_mapping

SCHEMA = "aegislake.dashboard.v1"
MAX_ALERTS = 20000
MAX_BYTES = 20 * 1024 * 1024


def _text(value: object, field: str, limit: int = 512) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"invalid dashboard {field}")
    return value


def normalize_alerts(alerts: object) -> list[dict]:
    """Accept only bounded, timezone-aware records; never emit arbitrary input fields."""
    if not isinstance(alerts, list) or len(alerts) > MAX_ALERTS:
        raise ValueError("dashboard requires at most 20000 alert windows")
    result, seen = [], set()
    for row in alerts:
        if not isinstance(row, dict):
            raise ValueError("invalid dashboard alert")
        identifier = _text(row.get("alert_id"), "alert ID")
        if identifier in seen:
            raise ValueError("duplicate dashboard alert ID")
        seen.add(identifier)
        stamp = datetime.fromisoformat(_text(row.get("window_start"), "timestamp", 64).replace("Z", "+00:00"))
        if stamp.tzinfo is None or not 2000 <= stamp.year <= 2200:
            raise ValueError("dashboard timestamps require a timezone and year 2000-2200")
        value = row.get("score")
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            raise ValueError("invalid dashboard score")
        if not 0 <= value <= 1:
            raise ValueError("dashboard ranking scores must be between 0 and 1")
        techniques = row.get("attack_hypotheses", [])
        if not isinstance(techniques, list) or len(techniques) > 64:
            raise ValueError("invalid dashboard techniques")
        techniques = sorted({_text(item, "technique", 128) for item in techniques})
        reasons = row.get("reasons", [])
        if not isinstance(reasons, list) or len(reasons) > 100:
            raise ValueError("invalid dashboard reasons")
        result.append({"alert_id": identifier, "user": _text(row.get("user"), "identity"),
                       "window_start": stamp.astimezone(timezone.utc).isoformat(), "score": float(value),
                       "model": _text(row.get("model", "unspecified"), "model", 128),
                       "attack_hypotheses": techniques,
                       "reasons": [_text(reason, "reason", 4096) for reason in reasons]})
    return sorted(result, key=lambda row: (-row["score"], row["alert_id"]))


def snapshot(report: dict, alerts: list[dict], *, kind: str = "evaluation") -> dict:
    if kind not in {"evaluation", "scoring"}:
        raise ValueError("unsupported dashboard batch kind")
    normalized = normalize_alerts(alerts)
    metrics = report.get("test", {}).get(report.get("champion")) if kind == "evaluation" else None
    # Scores, labels and data provenance are independent. Scoring batches have no effectiveness metrics.
    benchmark = None
    if metrics:
        benchmark = {key: metrics.get(key) for key in ("precision", "recall", "average_precision", "f1")}
    return {"schema": SCHEMA,
            "run": {"run_id": _text(report.get("run_id"), "run ID"), "kind": kind,
                    "data_kind": ("unlabeled" if kind == "scoring" else
                                  "synthetic" if report.get("config", {}).get("synthetic") is True else "labeled"),
                    "data_notice": str(report.get("data_notice", "Offline batch; collection scope unverified.")),
                    "model": str(report.get("champion", "unspecified")),
                    "capacity": report.get("capacity"), "benchmark": benchmark,
                    "bounds": report.get("split_boundaries", {}), "quality": report.get("quality", {})},
            "techniques": {key: {"name": item["name"],
                                  "candidate_tactics": describe_mapping([key])["techniques"][0]["candidate_tactics"]}
                           for key, item in TECHNIQUES.items()},
            "alerts": normalized}


def dashboard_page(data: dict | None = None, *, api: bool = False) -> str:
    from aegislake.dashboard_ui import BODY, SCRIPT, STYLE
    from aegislake.report import shell

    data = data or {"schema": SCHEMA, "run": {"run_id": "no-run", "data_kind": "unavailable"},
                    "techniques": {}, "alerts": []}
    encoded = json.dumps(data, ensure_ascii=True, allow_nan=False).replace("<", "\\u003c").replace("&", "\\u0026")
    body = BODY.replace("__API__", "true" if api else "false")
    body += '<script id="dashboard-data" type="application/json">' + encoded + "</script>"
    return shell({"run_id": data["run"]["run_id"],
                  "config": {"synthetic": data["run"].get("data_kind") == "synthetic"}},
                 "dashboards", "SOC dashboards", body, extra_style=STYLE, extra_script=SCRIPT, allow_api=api)


def write_dashboard(run_dir: Path, report: dict, alerts: list[dict], *, kind: str = "evaluation") -> None:
    data = snapshot(report, alerts, kind=kind)
    (run_dir / "dashboard.json").write_text(json.dumps(data, indent=2, allow_nan=False), encoding="utf-8")
    (run_dir / "dashboard.html").write_text(dashboard_page(data), encoding="utf-8")


def read_snapshot(path: Path) -> dict:
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("dashboard file exceeds 20 MiB")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != SCHEMA or not isinstance(data.get("run"), dict):
        raise ValueError("unsupported dashboard schema")
    run = data["run"]
    _text(run.get("run_id"), "run ID")
    if run.get("data_kind") not in {"synthetic", "labeled", "unlabeled"}:
        raise ValueError("invalid dashboard provenance")
    benchmark = run.get("benchmark")
    if run["data_kind"] == "unlabeled" and benchmark is not None:
        raise ValueError("unlabeled dashboard cannot claim effectiveness metrics")
    if benchmark is not None:
        if not isinstance(benchmark, dict):
            raise ValueError("invalid dashboard benchmark")
        for value in benchmark.values():
            if value is not None and (isinstance(value, bool) or not isinstance(value, (float, int))
                                      or not math.isfinite(value) or not 0 <= value <= 1):
                raise ValueError("invalid dashboard benchmark")
    data["alerts"] = normalize_alerts(data.get("alerts"))
    return data
