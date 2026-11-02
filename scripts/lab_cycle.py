"""Private lab evidence archives and the reviewed-release gate.

Run under the activity lock. Archives stay on the retained managed OS disk;
they are not off-VM backups. An unreadable/missing record blocks new activity.
"""
from datetime import datetime, timedelta, timezone
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import urllib.request
import uuid
from zoneinfo import ZoneInfo

RUN_ID = re.compile(r"activity-\d{8}T\d{6}Z")
SHA = re.compile(r"[0-9a-f]{40}")
REPOSITORY = "krlokbrera/aegislake"
CONFIG_FILES = [Path("/var/ossec/etc/ossec.conf"),
                Path("/var/ossec/etc/rules/local_rules.xml"),
                Path("/etc/systemd/system/aegis-activity.service")]
REQUIRED = {"ground-truth.json", "summary.json", "wazuh-alerts.ndjson",
            "auth-events.ndjson", "auth-events.ndjson.quality.json", "lake/quality.json"}
TOP_FILES = REQUIRED | {"run-metadata.json", "failure.json"}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
    temporary.replace(path)


def digest(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("Evidence must be a regular file")
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def code_fingerprint(repo):
    paths = {repo / "pyproject.toml"}
    for pattern in ["src/**/*.py", "scripts/*.py", "scripts/bootstrap-*.sh"]:
        paths.update(repo.glob(pattern))
    if not all(path.exists() for path in paths):
        raise ValueError("Missing code")
    return {path.relative_to(repo).as_posix(): digest(path) for path in sorted(paths)}


def configuration_fingerprint():
    return {str(path): digest(path) for path in CONFIG_FILES if path.exists()}


def provenance(repo):
    return {
        "commit": deployed_commit(repo), "code_fingerprint": code_fingerprint(repo),
        "configuration_fingerprint": configuration_fingerprint(),
        "python_packages": {name: importlib.metadata.version(name) for name in
                            ["aegislake", "pandas", "pyarrow", "duckdb", "numpy", "scikit-learn"]},
        "wazuh_packages": subprocess.run(
            ["dpkg-query", "-W", "-f=${Package} ${Version}\\n",
             "wazuh-manager", "wazuh-indexer", "wazuh-dashboard"],
            capture_output=True, text=True, check=False).stdout.splitlines(),
    }


def deployed_commit(repo):
    commit = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(
        ["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=no"], text=True)
    if not SHA.fullmatch(commit) or dirty.strip():
        raise ValueError("Expected a clean pinned deployment")
    return commit


def archive_dir(root, run_id):
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise ValueError("Invalid cycle identifier")
    return root / "archives" / run_id


def seal(root, folder):
    run_id = folder.name
    destination = archive_dir(root, run_id)
    if folder.resolve() != (root / "runs" / run_id).resolve() or folder.is_symlink():
        raise ValueError("Cycle must be in the private runs directory")
    if destination.exists():
        return verify_archive(root, run_id)
    staging = destination.with_name(run_id + ".pending-" + uuid.uuid4().hex)
    staging.mkdir(parents=True, mode=0o700)
    selected = {}
    for path in sorted(folder.rglob("*")):
        if path.is_symlink():
            raise ValueError("Symlinks are not evidence")
        if path.is_file():
            relative = path.relative_to(folder).as_posix()
            if relative in TOP_FILES or relative.startswith("lake/"):
                selected[relative] = digest(path)
    truth = read_json(folder / "ground-truth.json")
    if type(truth["started_unix"]) not in (int, float):
        raise ValueError("Invalid execution time")
    started = float(truth["started_unix"])
    if not (0 < started < 10**11):
        raise ValueError("Invalid execution time")
    day = datetime.fromtimestamp(started, ZoneInfo("Europe/Madrid")).date()
    with tarfile.open(staging / "batch.tar.gz", "x:gz") as archive:
        for name in selected:
            archive.add(folder / name, arcname=run_id + "/" + name, recursive=False)
    (staging / "batch.tar.gz").chmod(0o600)
    if selected != {name: digest(folder / name) for name in selected}:
        raise ValueError("Evidence changed during capture")
    manifest = {
        "schema": 1, "run_id": run_id, "started_unix": started,
        "review_due_date": (day + timedelta(days=1)).isoformat(),
        "sealed_at": datetime.now(timezone.utc).isoformat(),
        "complete": REQUIRED.issubset(selected), "files": selected,
        "archive_sha256": digest(staging / "batch.tar.gz"),
        "provenance_recorded_at_execution": "run-metadata.json" in selected,
        "storage": "private-retained-managed-os-disk",
    }
    atomic_json(staging / "manifest.json", manifest)
    staging.rename(destination)
    return manifest


def verify_archive(root, run_id):
    folder = archive_dir(root, run_id)
    if folder.is_symlink():
        raise ValueError("Archive must not be a symlink")
    manifest = read_json(folder / "manifest.json")
    if manifest["schema"] != 1 or manifest["run_id"] != run_id:
        raise ValueError("Manifest identity differs")
    if digest(folder / "batch.tar.gz") != manifest["archive_sha256"]:
        raise ValueError("Archive integrity failed")
    actual = {}
    with tarfile.open(folder / "batch.tar.gz", "r:gz") as archive:
        for member in archive:
            prefix = run_id + "/"
            if not member.isfile() or not member.name.startswith(prefix):
                raise ValueError("Unexpected archive member")
            relative = member.name[len(prefix):]
            if relative in actual or ".." in Path(relative).parts or Path(relative).is_absolute():
                raise ValueError("Unsafe archive member")
            with archive.extractfile(member) as stream:
                result = hashlib.sha256()
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    result.update(block)
                actual[relative] = result.hexdigest()
    if actual != manifest["files"]:
        raise ValueError("Manifest file hashes differ")
    return manifest


def archived_json(root, run_id, name):
    with tarfile.open(archive_dir(root, run_id) / "batch.tar.gz", "r:gz") as archive:
        member = archive.getmember(run_id + "/" + name)
        if not member.isfile() or member.size > 2_000_000:
            raise ValueError("Invalid JSON evidence")
        with archive.extractfile(member) as stream:
            return json.load(stream)


def analyze(root, run_id):
    manifest = verify_archive(root, run_id)
    report_path = archive_dir(root, run_id) / "analysis.json"
    manifest_hash = digest(archive_dir(root, run_id) / "manifest.json")
    if report_path.exists():
        previous = read_json(report_path)
        if previous.get("run_id") != run_id or previous.get("manifest_sha256") != manifest_hash:
            raise ValueError("Existing analysis describes different evidence")
        return previous
    summary = archived_json(root, run_id, "summary.json") if "summary.json" in manifest["files"] else {}
    truth = archived_json(root, run_id, "ground-truth.json")
    result = {
        "run_id": run_id, "archive_complete": manifest["complete"],
        "manifest_sha256": manifest_hash,
        "review_due_date": manifest["review_due_date"],
        "sessions_recorded": len(truth.get("steps", [])),
        "successful_sessions": summary.get("observed_successful_sessions"),
        "rejected_sessions": summary.get("observed_rejected_sessions"),
        "fim_alerts": summary.get("rule_counts", {}).get("550", 0),
        "adapter": summary.get("auth_adapter"), "lake": summary.get("lake"),
        "effectiveness_measured": False,
        "analysis_at": datetime.now(timezone.utc).isoformat(),
        "notes": "Machine reconciliation; scheduled review must evaluate causes and comparisons.",
    }
    atomic_json(archive_dir(root, run_id) / "analysis.json", result)
    return result


def github_validation(commit, pr_number, run_number):
    if (not SHA.fullmatch(commit) or type(pr_number) is not int or pr_number <= 0
            or type(run_number) is not int or run_number <= 0):
        raise ValueError("Invalid validation identifiers")

    def get(path):
        request = urllib.request.Request(
            "https://api.github.com/repos/" + REPOSITORY + path,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "AegisLake-lab-gate"})
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)

    pr = get("/pulls/" + str(pr_number))
    run = get("/actions/runs/" + str(run_number))
    if (pr["head"]["sha"] != commit or run["head_sha"] != commit
            or run["status"] != "completed" or run["conclusion"] != "success"
            or run.get("path", "").split("@")[0] != ".github/workflows/ci.yml"):
        raise ValueError("Final PR head and successful CI must match the deployed commit")
    return True


def approve(root, repo, run_id, validation, now=None, remote=github_validation):
    now = now or datetime.now(timezone.utc)
    manifest = verify_archive(root, run_id)
    folder = archive_dir(root, run_id)
    if now.tzinfo is None:
        raise ValueError("Timezone required")
    if now.astimezone(ZoneInfo("Europe/Madrid")).date().isoformat() < manifest["review_due_date"]:
        raise ValueError("Next-day review is not due yet")
    if not (folder / "analysis.json").is_file():
        raise ValueError("Analysis is required")
    for key in ["offline_validation_passed", "services_healthy", "review_complete"]:
        if validation.get(key) is not True:
            raise ValueError("Review, replay validation and service health must pass")
    if not isinstance(validation.get("rationale"), str) or not validation["rationale"].strip():
        raise ValueError("Review rationale is required")
    commit = deployed_commit(repo)
    if validation.get("commit") != commit:
        raise ValueError("Validation does not describe the deployed commit")
    remote(commit, validation["pr_number"], validation["ci_run_id"])
    record = {
        **validation, "run_id": run_id, "reviewed_at": now.isoformat(),
        "manifest_sha256": digest(folder / "manifest.json"),
        "analysis_sha256": digest(folder / "analysis.json"),
        "code_fingerprint": code_fingerprint(repo),
        "configuration_fingerprint": configuration_fingerprint(),
    }
    atomic_json(folder / "review.json", record)
    atomic_json(root / "evidence" / "iteration-state.json",
                {"run_id": run_id, "status": "ready", "review_due_date": manifest["review_due_date"],
                 "commit": commit, "reviewed_at": now.isoformat()})
    return record


def gate(root, repo, now=None, remote=github_validation):
    now = now or datetime.now(timezone.utc)
    try:
        attempt = read_json(root / "evidence" / "last-activity-attempt.json")
        candidates = []
        for path in (root / "archives").glob("activity-*/manifest.json"):
            manifest = read_json(path)
            if abs(manifest["started_unix"] - float(attempt["unix"])) < 2:
                candidates.append(manifest["run_id"])
        if len(candidates) != 1:
            return {"allowed": False, "reason": "latest_attempt_not_archived"}
        run_id = candidates[0]
        if attempt.get("run_id", run_id) != run_id:
            raise ValueError("Attempt identity differs")
        manifest = verify_archive(root, run_id)
        folder = archive_dir(root, run_id)
        record = read_json(folder / "review.json")
        if (record["run_id"] != run_id
                or record["manifest_sha256"] != digest(folder / "manifest.json")
                or record["analysis_sha256"] != digest(folder / "analysis.json")
                or record["code_fingerprint"] != code_fingerprint(repo)
                or record["configuration_fingerprint"] != configuration_fingerprint()
                or record["commit"] != deployed_commit(repo)):
            raise ValueError("Reviewed artifacts or code changed")
        if any(record.get(key) is not True for key in
               ["offline_validation_passed", "services_healthy", "review_complete"]):
            raise ValueError("Incomplete validation")
        reviewed = datetime.fromisoformat(record["reviewed_at"])
        if reviewed.tzinfo is None or reviewed > now:
            raise ValueError("Invalid review time")
        if reviewed.astimezone(ZoneInfo("Europe/Madrid")).date().isoformat() < manifest["review_due_date"]:
            raise ValueError("Review occurred before the required day")
        remote(record["commit"], record["pr_number"], record["ci_run_id"])
        return {"allowed": True, "reason": "reviewed_and_validated", "run_id": run_id}
    except (OSError, ValueError, KeyError, TypeError, tarfile.TarError, subprocess.SubprocessError):
        return {"allowed": False, "reason": "missing_or_invalid_review"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/var/lib/aegislake"))
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ["seal", "analyze", "approve"]:
        child = commands.add_parser(command)
        child.add_argument("--run-id", required=True)
        if command == "approve":
            child.add_argument("--validation-file", type=Path, required=True)
    commands.add_parser("gate")
    args = parser.parse_args()
    os.umask(0o077)
    lock_path = args.root / "evidence" / "activity.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    import fcntl
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.command == "seal":
            result = seal(args.root, args.root / "runs" / args.run_id)
        elif args.command == "analyze":
            result = analyze(args.root, args.run_id)
        elif args.command == "approve":
            result = approve(args.root, args.repo, args.run_id, read_json(args.validation_file))
            result = {"run_id": result["run_id"], "status": "ready", "commit": result["commit"]}
        else:
            result = gate(args.root, args.repo)
        print(json.dumps(result))


if __name__ == "__main__":
    main()
