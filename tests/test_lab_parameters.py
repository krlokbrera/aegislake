import base64
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("lab_parameters", ROOT / "scripts/lab_parameters.py")
parameters = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parameters)


def test_cloud_config_preserves_nested_shell_heredocs():
    source = "#!/bin/bash\ncat <<'SH'\nhello\nSH\n"
    config = json.loads(parameters.cloud_config(source).split("\n", 1)[1])
    entry = config["write_files"][0]
    assert base64.b64decode(entry["content"]).decode() == source
    assert entry["permissions"] == "0700"
    assert config["runcmd"] == [["bash", entry["path"]]]


def test_parameters_never_accept_private_key():
    with pytest.raises(ValueError):
        parameters.build_parameters(ROOT, "-----BEGIN OPENSSH PRIVATE KEY-----")
    with pytest.raises(ValueError):
        parameters.build_parameters(ROOT, "ssh-ed25519 AAAA\nssh-ed25519 BBBB")
    result = parameters.build_parameters(ROOT, "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA lab")
    for node in ["manager", "endpoint"]:
        config = json.loads(result["parameters"][node+"CloudConfig"]["value"].split("\n", 1)[1])
        assert base64.b64decode(config["write_files"][0]["content"]).startswith(b"#!/usr/bin/env bash")
