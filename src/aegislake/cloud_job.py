"""Finite Azure demo job. Upload reports before ephemeral storage disappears."""

from __future__ import annotations

import os
from pathlib import Path

from aegislake.azure import publish
from aegislake.pipeline import run
from aegislake.synthetic import generate


def main() -> None:
    account = os.environ["AEGIS_STORAGE_ACCOUNT"]
    root = Path("/app/runs")
    source = root / "demo-input.jsonl"
    generate(source)
    destination = run(source, root, synthetic=True)
    uploaded = publish(destination, account)
    # Only counts and synthetic run identifiers reach platform logs.
    print(f"Completed synthetic run {destination.name}: {len(uploaded)} private report objects")


if __name__ == "__main__":
    main()
