"""Private synthetic-report publication with Entra authentication and no shared keys."""

from __future__ import annotations

import json
import re
from pathlib import Path

from aegislake.scoring import verify_run

PUBLISH_FILES = ("report.html", "mitre.html", "report.json", "quality.json", "gold/alerts.json",
                 "attack-mapping.json", "dettect-techniques.yaml")


def publish(run_dir: Path, account: str, container: str = "reports") -> list[str]:
    if not re.fullmatch(r"[a-z0-9]{3,24}", account):
        raise ValueError("invalid Azure storage account name")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", container) or "--" in container:
        raise ValueError("invalid Azure container name")
    manifest = verify_run(run_dir)
    if manifest["config"].get("synthetic") is not True:
        raise ValueError("only synthetic demonstration reports may be published by this command")
    # Lazy imports leave the local demo independent of Azure packages and credentials.
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient, ContentSettings

    credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    uploaded = []
    try:
        with BlobServiceClient(f"https://{account}.blob.core.windows.net", credential=credential) as client:
            for relative in PUBLISH_FILES:
                path = run_dir / relative
                blob = f"{manifest['run_id']}/{relative}"
                mime = {".html": "text/html", ".yaml": "application/yaml"}.get(path.suffix, "application/json")
                with path.open("rb") as handle:
                    client.get_blob_client(container, blob).upload_blob(
                        handle, overwrite=True, content_settings=ContentSettings(content_type=mime)
                    )
                uploaded.append(blob)
            # Manifest is the commit marker, published only after all report uploads succeed.
            client.get_blob_client(container, f"{manifest['run_id']}/publication.json").upload_blob(
                json.dumps({"run_id": manifest["run_id"], "files": uploaded}),
                overwrite=True, content_settings=ContentSettings(content_type="application/json"),
            )
    finally:
        credential.close()
    return uploaded
