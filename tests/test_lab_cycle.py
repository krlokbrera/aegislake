from datetime import datetime, timezone
import importlib.util
import io
import json
from pathlib import Path
import sys
import time

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("lab_cycle", SCRIPTS / "lab_cycle.py")
cycle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cycle)
COMMIT = "a" * 40
RUN = "activity-20261102T124343Z"
LATER = datetime(2026, 11, 4, 12, 44, tzinfo=timezone.utc)


@pytest.fixture
def lab(tmp_path, monkeypatch):
    root = tmp_path / "private"
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='test'\n")
    (repo / "src").mkdir()
    (repo / "src/example.py").write_text("value = 1\n")
    monkeypatch.setattr(cycle, "deployed_commit", lambda path: COMMIT)
    monkeypatch.setattr(cycle, "CONFIG_FILES", [])
    folder = root / "runs" / RUN
    folder.mkdir(parents=True)
    start = datetime(2026, 11, 2, 12, 43, 43, tzinfo=timezone.utc).timestamp()
    for name in cycle.REQUIRED:
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n")
    cycle.atomic_json(folder / "ground-truth.json", {"started_unix": start, "steps": []})
    cycle.atomic_json(folder / "summary.json", {
        "observed_successful_sessions": 2, "observed_rejected_sessions": 8,
        "rule_counts": {"550": 1}, "auth_adapter": {"auth_events": 10},
        "lake": {"quality": {"accepted": 10, "rejected": 0}},
    })
    cycle.atomic_json(root / "evidence/last-activity-attempt.json", {"unix": start})
    return root, repo, folder


def validation():
    return {"commit": COMMIT, "pr_number": 15, "ci_run_id": 123,
            "offline_validation_passed": True, "services_healthy": True,
            "review_complete": True, "rationale": "Replay and service checks passed"}


def ready(lab):
    root, repo, folder = lab
    cycle.seal(root, folder)
    cycle.analyze(root, RUN)
    cycle.approve(root, repo, RUN, validation(),
                  now=LATER, remote=lambda *args: True)


def test_archive_is_private_and_preserves_original_snapshot(lab):
    root, repo, folder = lab
    manifest = cycle.seal(root, folder)
    assert manifest["complete"] is True
    assert manifest["provenance_recorded_at_execution"] is False
    assert manifest["review_due_date"] == "2026-11-03"
    archive = root / "archives" / RUN
    assert archive.stat().st_mode & 0o777 == 0o700
    assert (archive / "batch.tar.gz").stat().st_mode & 0o777 == 0o600
    (folder / "summary.json").write_text('{"modified": true}')
    assert cycle.archived_json(root, RUN, "summary.json")["observed_successful_sessions"] == 2
    assert cycle.verify_archive(root, RUN) == manifest


def test_private_paths_and_symlinks_are_not_archived(lab, tmp_path):
    root, repo, folder = lab
    (root / "outside-key").write_text("not part of the batch")
    (folder / "password.txt").write_text("not an allowed artifact")
    manifest = cycle.seal(root, folder)
    assert "password.txt" not in manifest["files"]
    other = root / "runs/activity-20261104T124343Z"
    other.mkdir()
    (other / "link").symlink_to(root / "outside-key")
    with pytest.raises(ValueError, match="Symlinks"):
        cycle.seal(root, other)
    with pytest.raises(ValueError):
        cycle.archive_dir(root, "../../outside")


def test_review_cannot_be_approved_on_execution_day(lab):
    root, repo, folder = lab
    cycle.seal(root, folder)
    cycle.analyze(root, RUN)
    early = datetime(2026, 11, 2, 23, tzinfo=timezone.utc)  # midnight Madrid is next day
    before = datetime(2026, 11, 2, 22, 59, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="not due yet"):
        cycle.approve(root, repo, RUN, validation(), now=before, remote=lambda *a: True)
    cycle.approve(root, repo, RUN, validation(), now=early, remote=lambda *a: True)
    assert cycle.gate(root, repo, now=LATER, remote=lambda *a: True)["allowed"]


def test_missing_review_blocks_and_valid_review_allows(lab):
    root, repo, folder = lab
    cycle.seal(root, folder)
    assert not cycle.gate(root, repo, now=LATER)["allowed"]
    ready(lab)
    assert cycle.gate(root, repo, now=LATER, remote=lambda *a: True)["allowed"]


@pytest.mark.parametrize("flag", ["offline_validation_passed", "services_healthy", "review_complete"])
def test_failed_validation_never_approves(lab, flag):
    root, repo, folder = lab
    cycle.seal(root, folder)
    cycle.analyze(root, RUN)
    record = validation()
    record[flag] = False
    with pytest.raises(ValueError, match="must pass"):
        cycle.approve(root, repo, RUN, record, now=LATER, remote=lambda *a: True)


@pytest.mark.parametrize("changed", ["archive", "analysis", "code", "config", "review"])
def test_any_changed_approved_input_blocks_the_next_run(lab, changed, monkeypatch):
    root, repo, folder = lab
    configuration = repo / "wazuh.xml"
    configuration.write_text("old")
    monkeypatch.setattr(cycle, "CONFIG_FILES", [configuration])
    ready(lab)
    archived = root / "archives" / RUN
    if changed == "archive":
        with (archived / "batch.tar.gz").open("ab") as stream:
            stream.write(b"tampered")
    elif changed == "analysis":
        (archived / "analysis.json").write_text("{}")
    elif changed == "code":
        (repo / "src/example.py").write_text("value = 2\n")
    elif changed == "config":
        configuration.write_text("changed")
    else:
        record = cycle.read_json(archived / "review.json")
        record["review_complete"] = False
        cycle.atomic_json(archived / "review.json", record)
    assert not cycle.gate(root, repo, now=LATER, remote=lambda *a: True)["allowed"]


def test_new_attempt_cannot_reuse_old_release(lab):
    root, repo, folder = lab
    ready(lab)
    cycle.atomic_json(root / "evidence/last-activity-attempt.json",
                      {"unix": LATER.timestamp(), "run_id": "activity-20261104T124400Z"})
    result = cycle.gate(root, repo, now=LATER, remote=lambda *a: True)
    assert result == {"allowed": False, "reason": "latest_attempt_not_archived"}


def test_remote_head_or_ci_failure_blocks_a_previously_approved_release(lab):
    root, repo, folder = lab
    ready(lab)
    def changed(*args):
        raise ValueError("PR changed or CI failed")
    assert not cycle.gate(root, repo, now=LATER, remote=changed)["allowed"]


@pytest.mark.parametrize("mismatch", ["pr_head", "ci_head", "ci_failed", "workflow"])
def test_github_checks_bind_to_exact_final_commit(monkeypatch, mismatch):
    def response(request, timeout):
        if "/pulls/" in request.full_url:
            payload = {"head": {"sha": "b"*40 if mismatch == "pr_head" else COMMIT}}
        else:
            payload = {"head_sha": "b"*40 if mismatch == "ci_head" else COMMIT,
                       "status": "completed", "conclusion": "failure" if mismatch == "ci_failed" else "success",
                       "path": "other.yml" if mismatch == "workflow" else ".github/workflows/ci.yml"}
        return io.BytesIO(json.dumps(payload).encode())
    monkeypatch.setattr(cycle.urllib.request, "urlopen", response)
    with pytest.raises(ValueError, match="must match"):
        cycle.github_validation(COMMIT, 15, 123)


def activity_module():
    spec = importlib.util.spec_from_file_location("activity", SCRIPTS / "run_lab_activity.py")
    activity = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(activity)
    return activity


def test_blocked_gate_does_not_probe_or_advance_attempt(lab, monkeypatch, capsys):
    root, repo, folder = lab
    activity = activity_module()
    state = root / "evidence/last-activity-attempt.json"
    cycle.atomic_json(state, {"unix": time.time() - 49 * 3600})
    before = state.read_bytes()
    monkeypatch.setattr(activity, "ROOT", root)
    monkeypatch.setattr(activity, "gate", lambda *args: {"allowed": False, "reason": "missing_review"})
    monkeypatch.setattr(activity, "perform_activity", lambda *args: pytest.fail("must not probe"))
    monkeypatch.setattr(sys, "argv", ["activity"])
    activity.main()
    assert "blocked_pending_cycle_review" in capsys.readouterr().out
    assert state.read_bytes() == before


def test_failed_exercise_is_archived_and_requires_another_review(lab, monkeypatch):
    root, repo, folder = lab
    activity = activity_module()
    cycle.atomic_json(root / "evidence/last-activity-attempt.json", {"unix": time.time() - 49 * 3600})
    config = repo / "config"
    config.mkdir()
    for name in ["activity_ed25519", "known_hosts"]:
        (config / name).write_text("test")
    monkeypatch.setattr(activity, "ROOT", root)
    monkeypatch.setattr(activity, "CONFIG", config)
    monkeypatch.setattr(activity, "gate", lambda *args: {"allowed": True, "run_id": RUN})
    monkeypatch.setattr(activity, "provenance", lambda *args: {"commit": COMMIT})
    def fail(*args):
        raise RuntimeError("controlled test failure")
    monkeypatch.setattr(activity, "perform_activity", fail)
    monkeypatch.setattr(sys, "argv", ["activity"])
    with pytest.raises(RuntimeError, match="controlled test failure"):
        activity.main()
    state = cycle.read_json(root / "evidence/iteration-state.json")
    assert state["status"] == "needs_analysis_and_review"
    assert state["complete"] is False
    assert (root / "archives" / state["run_id"] / "batch.tar.gz").exists()



def test_repeated_analysis_preserves_the_reviewed_hash(lab):
    root, repo, folder = lab
    ready(lab)
    reviewed = cycle.read_json(root / "archives" / RUN / "review.json")
    cycle.analyze(root, RUN)
    assert cycle.digest(root / "archives" / RUN / "analysis.json") == reviewed["analysis_sha256"]
    assert cycle.gate(root, repo, now=LATER, remote=lambda *a: True)["allowed"]



def test_installer_rejects_commit_substitution():
    spec = importlib.util.spec_from_file_location("install_cycle", SCRIPTS / "install_lab_cycle.py")
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)
    with pytest.raises(ValueError):
        installer.guest_script("main; touch /tmp/unsafe")
    script = installer.guest_script(COMMIT)
    assert "disable','--now','aegis-activity.timer" in script
    assert "start','aegis-activity.service" not in script


def test_github_validation_accepts_matching_successful_run(monkeypatch):
    def response(request, timeout):
        payload = ({"head": {"sha": COMMIT}} if "/pulls/" in request.full_url else
                   {"head_sha": COMMIT, "status": "completed", "conclusion": "success",
                    "path": ".github/workflows/ci.yml"})
        return io.BytesIO(json.dumps(payload).encode())
    monkeypatch.setattr(cycle.urllib.request, "urlopen", response)
    assert cycle.github_validation(COMMIT, 15, 123) is True
