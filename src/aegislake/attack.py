"""Curated ATT&CK hypotheses and conservative DeTT&CT administration exports."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

METADATA_DATE = "2026-10-31"
TACTIC_IDS = {
    "Initial Access": "TA0001", "Persistence": "TA0003",
    "Privilege Escalation": "TA0004", "Stealth": "TA0005", "Credential Access": "TA0006",
}
TACTICS = tuple(TACTIC_IDS)
TECHNIQUES = {
    "T1110.003": {
        "name": "Password Spraying", "tactics": ("Credential Access",),
        "url": "https://attack.mitre.org/techniques/T1110/003/",
        "description": "Attempts against many accounts can indicate an effort to acquire usable credentials.",
        "signal": "Shared source reaches at least 8 identities and the failure rate is at least 50%.",
        "caveat": "NAT, shared proxies and authentication outages can produce similar patterns. "
                  "Passwords are not observed; this signal cannot confirm password reuse.",
        "required_fields": ("timestamp", "user", "source", "success"),
    },
    "T1078": {
        "name": "Valid Accounts",
        "tactics": ("Initial Access", "Persistence", "Privilege Escalation", "Stealth"),
        "url": "https://attack.mitre.org/techniques/T1078/",
        "description": "Abuse of an existing account can support access, persistence or elevated privileges.",
        "signal": "An identity reaches at least 4 destinations in one closed 15-minute window.",
        "caveat": "Administrative work and approved changes may explain destination fanout. "
                  "The signal does not establish compromise or a specific adversary objective.",
        "required_fields": ("timestamp", "user", "destination"),
    },
}
DETTCT_SCOPE = "Unassessed SOC deployment (AegisLake candidate)"
DETTCT_NOTICE = (
    "DRAFT operational baseline, not an assessment of an existing SOC. No deployed detector "
    "or validated production visibility has been registered. Detection -1 means no detection; "
    "visibility 0 means no registered visibility. Review and replace these conservative "
    "placeholders before operational use. Alert counts and synthetic ML metrics do not set scores."
)


def describe_mapping(hypotheses: list[str]) -> dict:
    """Tactics describe catalog membership, never an inferred adversary objective."""
    techniques, unknown = [], []
    for identifier in sorted(set(hypotheses)):
        data = TECHNIQUES.get(identifier)
        if data is None:
            unknown.append(identifier)
            continue
        techniques.append({
            "technique_id": identifier, "technique_name": data["name"],
            "candidate_tactics": [{"tactic_id": TACTIC_IDS[name], "tactic_name": name}
                                 for name in data["tactics"]],
            "required_fields": list(data["required_fields"]), "reference": data["url"],
        })
    return {
        "status": "hypothesis", "metadata_checked": METADATA_DATE,
        "tactic_semantics": "Catalog membership; objectives are not established by the signal.",
        "techniques": techniques, "unmapped_technique_ids": unknown,
    }


def dettect_administration() -> dict:
    """Generate a v1.2 template without inventing operational detection/visibility scores."""
    techniques = []
    for identifier, data in TECHNIQUES.items():
        context = (f"Prototype signal: {data['signal']} Required canonical fields: "
                   f"{', '.join(data['required_fields'])}. No production assessment recorded.")
        techniques.append({
            "technique_id": identifier, "technique_name": data["name"],
            "detection": [{
                "applicable_to": [DETTCT_SCOPE], "location": [], "comment": context,
                "score_logbook": [{"date": None, "score": -1, "comment": DETTCT_NOTICE}],
            }],
            "visibility": [{
                "applicable_to": [DETTCT_SCOPE], "comment": context,
                "score_logbook": [{"date": None, "score": 0, "comment": DETTCT_NOTICE,
                                   "auto_generated": False}],
            }],
        })
    return {
        "version": 1.2, "file_type": "technique-administration",
        "name": "AegisLake candidate identity detections - DRAFT",
        "domain": "enterprise-attack", "platform": "all", "notes": DETTCT_NOTICE,
        "techniques": techniques,
    }


def yaml_text(value: object, indent: int = 0) -> str:
    """A minimal safe YAML emitter; quoted JSON scalars are valid YAML 1.2 scalars."""
    pad = " " * indent
    if isinstance(value, dict):
        lines = []
        for key, child in value.items():
            if isinstance(child, (dict, list)) and child:
                lines.append(f"{pad}{key}:\n{yaml_text(child, indent + 2)}")
            else:
                lines.append(f"{pad}{key}: {json.dumps(child, ensure_ascii=False, allow_nan=False)}")
        return "\n".join(lines)
    if isinstance(value, list):
        return "\n".join(f"{pad}-\n{yaml_text(child, indent + 2)}" if isinstance(child, (dict, list))
                         else f"{pad}- {json.dumps(child, ensure_ascii=False, allow_nan=False)}"
                         for child in value)
    raise TypeError("expected a mapping or list")


def write_attack_exports(run_dir: Path, report: dict, alerts: list[dict]) -> None:
    counts = Counter(identifier for alert in alerts for identifier in set(alert["attack_hypotheses"]))
    export = {
        "schema_version": 1, "run_id": report["run_id"], "status": "hypothesis",
        "metadata_checked": METADATA_DATE, "data_notice": report["data_notice"],
        "count_semantics": "Unique alert windows per technique. Technique/tactic counts can overlap.",
        "operational_assessment": "Not performed. DeTT&CT YAML is a draft deployment baseline.",
        "technique_counts": {identifier: counts[identifier] for identifier in TECHNIQUES},
        "alerts": [{"alert_id": alert["alert_id"], **describe_mapping(alert["attack_hypotheses"])}
                   for alert in alerts],
    }
    (run_dir / "attack-mapping.json").write_text(
        json.dumps(export, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
    )
    (run_dir / "dettect-techniques.yaml").write_text(yaml_text(dettect_administration()) + "\n", encoding="utf-8")
