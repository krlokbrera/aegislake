"""Adapt native Wazuh SSH authentication alerts without inventing MFA or labels."""
from __future__ import annotations

import argparse
import ipaddress
import json
from pathlib import Path
import re

from aegislake.adapters import pseudonym
from aegislake.contracts import canonical_event

PATTERNS = [
    (True, re.compile(r"\bAccepted (?:publickey|password|keyboard-interactive(?:/pam)?) for (\S+) from (\S+) port (\d+)")),
    (False, re.compile(r"\bFailed (?:publickey|password|keyboard-interactive(?:/pam)?) for (?:invalid user )?(\S+) from (\S+) port (\d+)")),
    (False, re.compile(r"\bInvalid user (\S+) from (\S+) port (\d+)")),
]


def auth_event(alert: dict, key: bytes) -> dict | None:
    if not isinstance(alert, dict):
        raise ValueError("expected an alert object")
    decoder = alert.get("decoder") or {}
    if not isinstance(decoder, dict) or not any(
        str(decoder.get(field, "")).startswith("sshd") for field in ["name", "parent"]
    ):
        return None
    text = alert.get("full_log")
    if not isinstance(text, str):
        raise ValueError("SSH alert has no raw log")
    match = None
    success = False
    for outcome, pattern in PATTERNS:
        match = pattern.search(text)
        if match:
            success = outcome
            break
    if not match:
        return None
    user, address, _ = match.groups()
    ipaddress.ip_address(address)
    agent = alert.get("agent") or {}
    host = agent.get("name") or agent.get("id") if isinstance(agent, dict) else None
    if not isinstance(host, str) or not host:
        raise ValueError("missing agent identity")
    # Duplicate base/correlation alerts carrying the identical OS log share an ID.
    return canonical_event({
        "event_id":pseudonym(host + ":" + text, key, "event"),
        "timestamp":alert.get("timestamp"),
        "user":pseudonym(user, key, "user"),
        "source":pseudonym(address, key, "source"),
        "destination":pseudonym(host, key, "host"),
        "success":success, "mfa":None, "country":"unknown",
        "label":None, "scenario":"unlabeled-wazuh",
    })


def adapt_alerts(source: Path, destination: Path, key: bytes) -> dict:
    if len(key) < 32:
        raise ValueError("pseudonymization key must contain at least 32 bytes")
    if source.resolve() == destination.resolve():
        raise ValueError("source and destination must differ")
    quality = destination.with_suffix(destination.suffix + ".quality.json")
    if destination.exists() or quality.exists():
        raise FileExistsError("export already exists")
    stats = {"records":0,"auth_events":0,"duplicates":0,"ignored":0,"malformed":0}
    events = {}
    with source.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            stats["records"] += 1
            try:
                if len(line) > 1_000_000:
                    raise ValueError("oversize log record")
                event = auth_event(json.loads(line), key)
            except (ValueError, TypeError, KeyError):
                stats["malformed"] += 1
                continue
            if event is None:
                stats["ignored"] += 1
            elif event["event_id"] in events:
                stats["duplicates"] += 1
            else:
                events[event["event_id"]] = event
    stats["auth_events"] = len(events)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as handle:
        for event in sorted(events.values(), key=lambda value:value["timestamp"]):
            handle.write(json.dumps(event, sort_keys=True) + "\n")
    with quality.open("x", encoding="utf-8") as handle:
        json.dump(stats, handle, indent=2)
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--key-file", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(adapt_alerts(args.input,args.output,args.key_file.read_bytes())))


if __name__ == "__main__":
    main()
