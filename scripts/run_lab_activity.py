"""Generate bounded activity against the dedicated private AegisLake endpoint.

Run as root on the Wazuh manager. Evidence remains private on that VM.
The hourly timer checks a 48-hour minimum interval; it does not generate hourly
SSH probes. Failure also advances the attempt timestamp to avoid retry storms.
"""
from datetime import datetime, timezone
import argparse
import fcntl
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time

from lab_cycle import atomic_json, gate, provenance, seal

TARGET = "10.77.0.5"
ROOT = Path("/var/lib/aegislake")
CONFIG = Path("/etc/aegislake")
INTERVAL_SECONDS = 48 * 3600
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))



def due(previous, now):
    if previous is None:
        return True
    elapsed = now - float(previous)
    return elapsed >= INTERVAL_SECONDS


def ssh_args(user, command):
    if user != "aegis-lab" and user not in {f"aegis-probe-{i}" for i in range(8)}:
        raise ValueError("Only the dedicated lab users are permitted")
    if command not in {"baseline", "fim"}:
        raise ValueError("Unknown lab action")
    return [
        "ssh", "-F", "/dev/null", "-i", str(CONFIG / "activity_ed25519"),
        "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes",
        "-o", "PreferredAuthentications=publickey",
        "-o", "PasswordAuthentication=no", "-o", "KbdInteractiveAuthentication=no",
        "-o", "StrictHostKeyChecking=yes",
        "-o", "UserKnownHostsFile=" + str(CONFIG / "known_hosts"),
        "-o", "ConnectTimeout=5", "-o", "ConnectionAttempts=1",
        "-o", "ClearAllForwardings=yes", user + "@" + TARGET, command,
    ]


def analyze_auth_events(source, destination):
    from aegislake.lake import ingest

    frame, quality = ingest(source, destination)
    return {
        "quality": quality, "users": int(frame["user"].nunique()),
        "sources": int(frame["source"].nunique()),
        "successful_auth_events": int(frame["success"].eq(True).sum()),
        "failed_auth_events": int(frame["success"].eq(False).sum()),
        "effectiveness_measured": False,
    }


def export_alerts(folder, started):
    sys.path.insert(0, str(REPO / "src"))
    from aegislake.wazuh import adapt_alerts

    source = Path("/var/ossec/logs/alerts/alerts.json")
    raw = folder / "wazuh-alerts.ndjson"
    counts = {}
    event_times = []
    with raw.open("x") as output:
        with source.open() as stream:
            for line in stream:
                try:
                    item = json.loads(line)
                    stamp = datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00"))
                    if stamp.timestamp() < started - 5:
                        continue
                    if item.get("agent", {}).get("name") != "aegis-endpoint":
                        continue
                    output.write(json.dumps(item) + "\n")
                    rule = str(item.get("rule", {}).get("id", "unknown"))
                    counts[rule] = counts.get(rule, 0) + 1
                    event_times.append(stamp.timestamp())
                except (ValueError, KeyError, TypeError):
                    continue
    key_file = CONFIG / "pseudonym.key"
    if not key_file.exists():
        descriptor = os.open(key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(secrets.token_bytes(32))
    quality = adapt_alerts(raw, folder / "auth-events.ndjson", key_file.read_bytes())
    lake = analyze_auth_events(folder / "auth-events.ndjson", folder / "lake") if quality["auth_events"] else None
    return {
        "rule_counts": counts, "auth_adapter": quality, "lake": lake,
        "first_alert_seconds": max(0, min(event_times) - started) if event_times else None,
        "interpretation": "Controlled lab telemetry; attack effectiveness and ML accuracy unmeasured.",
    }



def perform_activity(folder, now):
    steps = []
    scenarios = [("aegis-lab", "baseline")]
    scenarios.extend((f"aegis-probe-{i}", "baseline") for i in range(8))
    scenarios.append(("aegis-lab", "fim"))
    for user, action in scenarios:
        at = datetime.now(timezone.utc).isoformat()
        try:
            result = subprocess.run(
                ssh_args(user, action), capture_output=True, text=True, timeout=15,
                check=False,
            )
            step = {"at": at, "user": user, "action": action, "returncode": result.returncode,
                    "expected_success": user == "aegis-lab",
                    "stdout": result.stdout[:1000], "stderr": result.stderr[:1000]}
        except subprocess.TimeoutExpired:
            step = {"at": at, "user": user, "action": action, "returncode": None,
                    "expected_success": user == "aegis-lab", "timeout": True}
        steps.append(step)
        atomic_json(folder / "ground-truth.json",
                    {"started_unix": now, "scope": "owned-private-lab-only", "steps": steps})
        time.sleep(1)
    time.sleep(45)
    summary = export_alerts(folder, now)
    summary["sessions"] = len(steps)
    summary["expected_successful_sessions"] = 2
    summary["observed_successful_sessions"] = sum(s["returncode"] == 0 for s in steps)
    summary["expected_rejected_sessions"] = 8
    summary["observed_rejected_sessions"] = sum(
        s["returncode"] == 255 for s in steps if not s["expected_success"])
    summary["run"] = folder.name
    atomic_json(folder / "summary.json", summary)
    print(json.dumps(summary))
    if summary["observed_successful_sessions"] != 2:
        raise RuntimeError("Lab SSH session failed; inspect private ground truth")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    os.umask(0o077)
    evidence = ROOT / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    with (evidence / "activity.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = evidence / "last-activity-attempt.json"
        now = time.time()
        previous = json.loads(state.read_text())["unix"] if state.exists() else None
        if not due(previous, now):
            print(json.dumps({"status": "not_due", "minimum_interval_hours": 48}))
            return
        release = gate(ROOT, REPO)
        if not release["allowed"]:
            print(json.dumps({"status": "blocked_pending_cycle_review", **release}))
            return
        for required in ["activity_ed25519", "known_hosts"]:
            if not (CONFIG / required).is_file():
                raise RuntimeError("Missing private lab SSH configuration")
        name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        folder = ROOT / "runs" / ("activity-" + name)
        folder.mkdir(parents=True, exist_ok=False)
        atomic_json(folder / "run-metadata.json", {
            **provenance(REPO),
            "started_unix": now, "previous_reviewed_cycle": release["run_id"],
        })
        atomic_json(folder / "ground-truth.json",
                    {"started_unix": now, "scope": "owned-private-lab-only", "steps": []})
        atomic_json(state, {"unix": now, "utc": datetime.now(timezone.utc).isoformat(),
                            "run_id": folder.name})
        try:
            perform_activity(folder, now)
        except Exception as error:
            atomic_json(folder / "failure.json", {"error_type": type(error).__name__})
            raise
        finally:
            manifest = seal(ROOT, folder)
            atomic_json(evidence / "iteration-state.json", {
                "run_id": folder.name, "status": "needs_analysis_and_review",
                "review_due_date": manifest["review_due_date"], "complete": manifest["complete"],
            })


if __name__ == "__main__":
    main()
