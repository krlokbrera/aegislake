"""Human review ledger. No changes to accounts, endpoints, or cloud permissions."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DECISIONS = {"true_positive", "false_positive", "needs_context"}


def alert_id(user: str, window_start: str) -> str:
    return hashlib.sha256(f"{user}|{window_start}".encode()).hexdigest()[:24]


def record_review(run_dir: Path, identifier: str, decision: str, reviewer: str, note: str = "") -> None:
    if decision not in DECISIONS:
        raise ValueError("invalid review decision")
    if not reviewer.strip() or len(reviewer) > 80 or len(note) > 2000:
        raise ValueError("reviewer required; use an alias and short nonsensitive note")
    alerts = json.loads((run_dir / "gold" / "alerts.json").read_text(encoding="utf-8"))
    if identifier not in {item["alert_id"] for item in alerts}:
        raise ValueError("unknown alert_id")
    connection = sqlite3.connect(run_dir / "reviews.sqlite")
    try:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS reviews
            (id INTEGER PRIMARY KEY, alert_id TEXT NOT NULL, decision TEXT NOT NULL,
             reviewer TEXT NOT NULL, note TEXT NOT NULL, reviewed_at TEXT NOT NULL)"""
        )
        connection.execute(
            "INSERT INTO reviews (alert_id,decision,reviewer,note,reviewed_at) VALUES (?,?,?,?,?)",
            (identifier, decision, reviewer, note, datetime.now(timezone.utc).isoformat()),
        )
        connection.commit()
    finally:
        connection.close()
