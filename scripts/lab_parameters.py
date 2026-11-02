"""Build ARM parameters from public SSH key and the reviewed bootstrap scripts."""
import argparse
import base64
import json
import os
from pathlib import Path
import re


def cloud_config(source):
    # JSON is valid YAML. Base64 keeps shell heredocs intact.
    return "#cloud-config\n" + json.dumps({
        "write_files": [{
            "path": "/usr/local/sbin/aegislake-bootstrap",
            "permissions": "0700", "owner": "root:root", "encoding": "b64",
            "content": base64.b64encode(source.encode()).decode(),
        }],
        "runcmd": [["bash", "/usr/local/sbin/aegislake-bootstrap"]],
    })


def build_parameters(root, public_key):
    public_key = public_key.strip()
    if not re.fullmatch(r"ssh-ed25519 [A-Za-z0-9+/=]+(?: [^\r\n]*)?", public_key):
        raise ValueError("Expected a single Ed25519 public SSH key, never a private key")
    values = {"sshPublicKey": public_key}
    for node, source in [("manager", "bootstrap-wazuh.sh"), ("endpoint", "bootstrap-endpoint.sh")]:
        values[node + "CloudConfig"] = cloud_config((root / "scripts" / source).read_text())
    return {
        "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
        "contentVersion": "1.0.0.0",
        "parameters": {name: {"value": value} for name, value in values.items()},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-public-key", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_parameters(Path(__file__).resolve().parents[1], args.ssh_public_key.read_text())
    os.umask(0o077)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)


if __name__ == "__main__":
    main()
