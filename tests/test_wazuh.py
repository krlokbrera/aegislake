import json

import pytest

from aegislake.wazuh import adapt_alerts, auth_event

KEY = b"wazuh-test-only-key-32-bytes-long!!"


def alert(message):
    return {"timestamp":"2026-11-02T12:00:00.000+0000","decoder":{"name":"sshd"},
            "agent":{"name":"lab-host"},"full_log":message}


def test_failed_auth_is_pseudonymized_and_never_labeled():
    value = auth_event(alert("sshd[12]: Failed publickey for invalid user labuser from 10.77.0.4 port 48102 ssh2"),KEY)
    assert value["success"] is False
    assert value["mfa"] is None and value["label"] is None and value["country"] == "unknown"
    assert value["scenario"] == "unlabeled-wazuh"
    assert "labuser" not in json.dumps(value) and "10.77.0.4" not in json.dumps(value)
    assert value["timestamp"].endswith("+00:00")


def test_accepted_auth_is_success_without_claiming_mfa():
    value = auth_event(alert("Accepted publickey for worker from 2001:db8::1 port 55000 ssh2"),KEY)
    assert value["success"] is True and value["mfa"] is None


def test_unknown_user_connection_is_a_failed_auth_log_event():
    assert auth_event(alert("Invalid user labuser from 10.77.0.4 port 45100"),KEY)["success"] is False


def test_non_auth_host_alerts_are_excluded():
    value = {"decoder":{"name":"syscheck"},"full_log":"Integrity checksum changed","agent":{"name":"host"}}
    assert auth_event(value,KEY) is None
    assert auth_event(alert("Connection closed by authenticating user worker"),KEY) is None


def test_duplicate_correlated_os_logs_share_id():
    one = alert("Invalid user labuser from 10.77.0.4 port 45100")
    two = dict(one,id="a-different-wazuh-id",rule={"id":"5712"})
    assert auth_event(one,KEY)["event_id"] == auth_event(two,KEY)["event_id"]


def test_invalid_address_and_naive_timestamp_are_rejected():
    with pytest.raises(ValueError):
        auth_event(alert("Invalid user labuser from invalid-address port 45100"),KEY)
    item = alert("Invalid user labuser from 10.77.0.4 port 45100")
    item["timestamp"] = "2026-11-02T12:00:00"
    with pytest.raises(ValueError):
        auth_event(item,KEY)


def test_adapter_counts_bad_records_without_exporting_raw_content(tmp_path):
    source = tmp_path / "alerts.json"
    event = alert("Invalid user labuser from 10.77.0.4 port 45100")
    source.write_text(json.dumps(event)+"\n"+json.dumps(event)+"\nnot-json\n"+json.dumps({"decoder":{"name":"syscheck"}})+"\n")
    destination = tmp_path / "events.ndjson"
    stats = adapt_alerts(source,destination,KEY)
    assert stats == {"records":4,"auth_events":1,"duplicates":1,"ignored":1,"malformed":1}
    assert "labuser" not in destination.read_text()
    with pytest.raises(FileExistsError):
        adapt_alerts(source,destination,KEY)
    with pytest.raises(ValueError):
        adapt_alerts(source,source,KEY)


def test_empty_export_and_short_key(tmp_path):
    source = tmp_path / "alerts.json"
    source.write_text("")
    with pytest.raises(ValueError):
        adapt_alerts(source,tmp_path/"short.ndjson",b"short")
    assert adapt_alerts(source,tmp_path/"empty.ndjson",KEY)["auth_events"] == 0
