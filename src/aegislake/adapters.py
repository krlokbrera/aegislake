"""Local Microsoft Graph export adapter. No live API permissions are requested."""

from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

from aegislake.contracts import canonical_event


def pseudonym(value: str, key: bytes, namespace: str) -> str:
    if len(key) < 32:
        raise ValueError("pseudonymization key must contain at least 32 bytes")
    return namespace + "-" + hmac.new(key, (namespace + ":" + value).encode(), hashlib.sha256).hexdigest()[:32]


def entra_event(value: dict, key: bytes) -> dict:
    for field in ("id", "createdDateTime", "userId", "ipAddress"):
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise ValueError("Graph event missing required identity fields")
    target = value.get("resourceId") or value.get("appId")
    status = value.get("status")
    if not target or not isinstance(status, dict) or type(status.get("errorCode")) is not int:
        raise ValueError("Graph event missing destination or status")
    # authenticationRequirement describes a policy, not proof an MFA step succeeded.
    steps = value.get("authenticationDetails") or []
    mfa_steps = [step for step in steps if isinstance(step, dict)
                 and step.get("authenticationStepRequirement") == "multiFactorAuthentication"]
    mfa = any(step.get("succeeded") is True for step in mfa_steps) if mfa_steps else None
    location = value.get("location") or {}
    if not isinstance(location, dict):
        location = {}
    return canonical_event({
        "event_id": pseudonym(value["id"], key, "event"),
        "timestamp": value["createdDateTime"],
        "user": pseudonym(value["userId"], key, "user"),
        "source": pseudonym(value["ipAddress"], key, "source"),
        "destination": pseudonym(str(target), key, "resource"),
        "success": status["errorCode"] == 0,
        "mfa": mfa, "country": location.get("countryOrRegion") or "unknown",
        "label": None, "scenario": "unlabeled",
    })


def adapt_entra(source: Path, destination: Path, key: bytes) -> int:
    document = json.loads(source.read_text(encoding="utf-8"))
    records = document.get("value") if isinstance(document, dict) else document
    if not isinstance(records, list):
        raise ValueError("expected Graph value array or array of sign-in objects")
    if destination.resolve() == source.resolve():
        raise ValueError("source and destination must differ")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive create avoids overwriting a prior export. Validate all events first.
    events = [entra_event(row, key) for row in records]
    with destination.open("x", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
    return len(events)
