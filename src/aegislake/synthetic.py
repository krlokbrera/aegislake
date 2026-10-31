"""Seeded identity telemetry. Labels describe a simulator, never real effectiveness."""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path


def generate(path: Path, *, days: int = 30, users: int = 50, seed: int = 42) -> int:
    if days < 15 or users < 10:
        raise ValueError("demo requires at least 15 days and 10 users")
    rng = random.Random(seed)
    start = datetime(2026, 1, 5, tzinfo=timezone.utc)
    rows: list[dict] = []

    def add(stamp, user, source, destination, success, mfa, country, label, scenario):
        rows.append({
            "event_id": f"syn-{len(rows):09d}",
            "timestamp": stamp.isoformat(),
            "user": user, "source": source, "destination": destination,
            "success": success, "mfa": mfa, "country": country,
            "label": label, "scenario": scenario,
        })

    for day in range(days):
        base = start + timedelta(days=day)
        for uid in range(users):
            user = f"employee-{uid:04d}"
            # Benign overlap: occasional off-hours, failed MFA, travel and busy service users.
            for _ in range(rng.randint(8, 16)):
                hour = rng.randint(8, 18) if rng.random() < 0.94 else rng.randrange(24)
                stamp = base + timedelta(hours=hour, minutes=rng.randrange(60), seconds=rng.randrange(60))
                country = "ES" if rng.random() < 0.96 else rng.choice(["PT", "FR", "DE"])
                add(stamp, user, f"workstation-{uid:04d}", f"app-{rng.randrange(6):02d}",
                    rng.random() > 0.07, rng.random() > 0.025, country, 0, "routine")
        for _ in range(4):
            uid = rng.randrange(users)
            stamp = base + timedelta(hours=rng.randint(8, 18), minutes=rng.randrange(60))
            for n in range(rng.randint(8, 15)):
                add(stamp + timedelta(seconds=n), f"employee-{uid:04d}",
                    f"workstation-{uid:04d}", "app-00", False, True, "ES", 0, "stale_password")
        for _ in range(3):
            uid = rng.randrange(users)
            stamp = base + timedelta(hours=rng.randrange(24), minutes=rng.randrange(60))
            for n in range(rng.randint(12, 25)):
                add(stamp + timedelta(seconds=n), f"service-{uid:04d}", f"runner-{uid:04d}",
                    f"app-{n % 6:02d}", True, False, "ES", 0, "batch_service")
        # Daily attack campaigns recur across distinct temporal splits; deliberately include overlap.
        stamp = base + timedelta(hours=rng.randrange(24), minutes=rng.randrange(50))
        for n in range(rng.randint(18, 35)):
            uid = rng.randrange(users)
            add(stamp + timedelta(seconds=3 * n), f"employee-{uid:04d}",
                f"gateway-{day:03d}", "app-00", False, rng.random() > 0.3,
                rng.choice(["ES", "FR", "NL"]), 1, "password_spray")
        uid = rng.randrange(users)
        stamp = base + timedelta(hours=rng.randrange(24), minutes=rng.randrange(50))
        for n in range(rng.randint(10, 24)):
            add(stamp + timedelta(seconds=4 * n), f"employee-{uid:04d}",
                f"workstation-{uid:04d}", f"admin-{n % 12:02d}", True,
                rng.random() > 0.5, rng.choice(["ES", "DE", "US"]), 1, "account_abuse")
        # An intentionally subtle attack the detector may miss.
        uid = rng.randrange(users)
        add(base + timedelta(hours=10, minutes=15), f"employee-{uid:04d}",
            f"workstation-{uid:04d}", "app-02", True, True, "ES", 1, "stealth_access")
    rows.sort(key=lambda row: (row["timestamp"], row["event_id"]))
    # Replay duplicate and malformed records exercise ingestion quality controls.
    rows.extend([dict(rows[3]), {"event_id": "bad-demo-record", "timestamp": "invalid"}])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    return len(rows)
