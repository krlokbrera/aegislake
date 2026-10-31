"""Strict canonical event contract. Ground truth never enters model features."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

REQUIRED = {"event_id", "timestamp", "user", "source", "destination", "success", "mfa", "country"}
OPTIONAL = {"label", "scenario"}
MAX_FIELD_LENGTH = 200


def canonical_event(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("event must be an object")
    if REQUIRED - value.keys():
        raise ValueError("missing required fields")
    if value.keys() - REQUIRED - OPTIONAL:
        raise ValueError("unknown fields")
    result = dict(value)
    for key in REQUIRED - {"timestamp", "success", "mfa"}:
        if not isinstance(result[key], str) or not result[key].strip():
            raise ValueError("identifier must be a nonempty string")
        if len(result[key]) > MAX_FIELD_LENGTH:
            raise ValueError("identifier too long")
    if type(result["success"]) is not bool:
        raise ValueError("success must be a JSON boolean")
    if result["mfa"] is not None and type(result["mfa"]) is not bool:
        raise ValueError("mfa must be a JSON boolean or null")
    if not isinstance(result["timestamp"], str):
        raise ValueError("timestamp must be ISO 8601 text")
    try:
        stamp = datetime.fromisoformat(result["timestamp"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if stamp.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    if not 1970 <= stamp.year <= 2100:
        raise ValueError("timestamp year outside supported range")
    result["timestamp"] = stamp.astimezone(timezone.utc).isoformat()
    label = result.get("label")
    if label is not None and (type(label) is not int or label not in (0, 1)):
        raise ValueError("label must be 0, 1, or null")
    result["label"] = label
    scenario = result.get("scenario", "unknown")
    if not isinstance(scenario, str) or len(scenario) > MAX_FIELD_LENGTH:
        raise ValueError("invalid scenario")
    result["scenario"] = scenario
    return result


def content_digest(event: dict) -> str:
    payload = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode()).hexdigest()
