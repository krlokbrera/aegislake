from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def module(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


activity = module("run_lab_activity")
installer = module("install_lab_activity")


def test_activity_cadence_and_clock_rollback():
    now = datetime.now(timezone.utc).timestamp()
    assert activity.due(None, now)
    assert not activity.due(now - 47 * 3600, now)
    assert activity.due(now - 48 * 3600, now)
    assert not activity.due(now + 60, now)


def test_activity_rejects_arbitrary_users_and_commands():
    with pytest.raises(ValueError):
        activity.ssh_args("root", "baseline")
    with pytest.raises(ValueError):
        activity.ssh_args("aegis-lab", "id; curl example.invalid")
    args = activity.ssh_args("aegis-probe-7", "baseline")
    assert args[-2:] == ["aegis-probe-7@10.77.0.5", "baseline"]
    assert "StrictHostKeyChecking=yes" in args
    assert "PasswordAuthentication=no" in args


def test_public_key_requires_valid_type_and_discards_comment():
    assert installer.public_key("notice\nssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA root@lab") == (
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA")
    with pytest.raises(ValueError):
        installer.public_key("ssh-rsa AAAAB unsafe")
    with pytest.raises(ValueError):
        installer.public_key("ssh-ed25519 $(cat /etc/shadow)")


def test_guest_error_is_not_reported_as_success(monkeypatch):
    response = {"value": [{"message": "Enable succeeded:\n[stdout]\nready\n[stderr]\nfailed"}]}
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(
        a, 0, json.dumps(response), ""))
    with pytest.raises(RuntimeError, match="Guest command reported"):
        installer.invoke("test", "aegis-endpoint", "echo ready")
    with pytest.raises(ValueError):
        installer.invoke("test", "outside-lab", "echo ready")


def test_missing_guest_markers_are_rejected(monkeypatch):
    response = {"value": [{"message": "not a valid guest response"}]}
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(
        a, 0, json.dumps(response), ""))
    with pytest.raises(RuntimeError, match="Unexpected Run Command"):
        installer.invoke("test", "aegis-wazuh", "echo ready")
