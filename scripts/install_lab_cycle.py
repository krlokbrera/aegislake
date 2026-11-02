"""Deploy an exact CI-validated lab-cycle PR to the existing Wazuh manager.

Uses the signed-in operator and the existing private managed disk. Does not
create resources, grant roles, change networking or bypass the credit guard.
"""
import argparse
import json

from install_lab_activity import invoke
from lab_cycle import SHA, github_validation


def guest_script(commit):
    if not isinstance(commit, str) or not SHA.fullmatch(commit):
        raise ValueError("Expected an exact commit SHA")
    source = "commit=" + repr(commit) + """
import fcntl,hashlib,json,subprocess,sys
from pathlib import Path
root=Path('/var/lib/aegislake')
repo=Path('/opt/aegislake-cycle')
url='https://github.com/krlokbrera/aegislake.git'
def run(args):
    return subprocess.run(args,capture_output=True,text=True,check=True).stdout.strip()
run(['systemctl','disable','--now','aegis-activity.timer'])
if not repo.exists():
    repo.mkdir(mode=0o700)
    run(['git','init','-q',str(repo)])
    run(['git','-C',str(repo),'remote','add','origin',url])
if not (repo/'.git').is_dir() or run(['git','-C',str(repo),'remote','get-url','origin']) != url:
    raise RuntimeError('Refusing an unrelated checkout')
if run(['git','-C',str(repo),'status','--porcelain','--untracked-files=no']):
    raise RuntimeError('Preserve tracked local changes before deploying')
run(['git','-C',str(repo),'fetch','-q','--depth','1','origin',commit])
run(['git','-C',str(repo),'checkout','-q','--detach',commit])
sys.path.insert(0,str(repo/'scripts'))
from lab_cycle import atomic_json,seal,analyze,gate,digest
attempt=root/'evidence/last-activity-attempt.json'
before=digest(attempt)
with (root/'evidence/activity.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    archives=[]
    for folder in sorted((root/'runs').glob('activity-*')):
        if folder.is_dir() and (folder/'ground-truth.json').is_file():
            manifest=seal(root,folder)
            analyze(root,folder.name)
            archives.append({'run_id':folder.name,'complete':manifest['complete'],
                             'review_due_date':manifest['review_due_date']})
    if not archives:
        raise RuntimeError('Import an existing baseline exercise before enabling the gate')
    latest=archives[-1]
    atomic_json(root/'evidence/iteration-state.json',
                {**latest,'status':'needs_analysis_and_review','deployed_commit':commit})
    unit=Path('/etc/systemd/system/aegis-activity.service')
    text=unit.read_text()
    backup=root/'evidence/activity-service.before-cycle'
    if not backup.exists():
        backup.write_text(text)
        backup.chmod(0o600)
    old='/opt/aegislake/scripts/run_lab_activity.py'
    new='/opt/aegislake-cycle/scripts/run_lab_activity.py'
    if old not in text and new not in text:
        raise RuntimeError('Unexpected activity unit; review before changing it')
    unit.write_text(text.replace(old,new))
    unit.chmod(0o644)
    atomic_json(root/'evidence/cycle-deployment.json',
                {'commit':commit,'repo':str(repo),'archived_cycles':archives})
run(['systemctl','daemon-reload'])
run(['systemctl','enable','--now','aegis-activity.timer'])
# Do not start the service manually: the hourly timer owns simulation cadence.
print(json.dumps({'deployed_commit':commit,'repo':str(repo),'archives':archives,
                  'gate':gate(root,repo),'attempt_unchanged':before==digest(attempt),
                  'services':{name:subprocess.run(['systemctl','is-active',name],
                      capture_output=True,text=True).stdout.strip() for name in
                      ['aegis-activity.timer','wazuh-manager','wazuh-indexer','wazuh-dashboard']}}))
"""
    return "set -eu\numask 077\npython3 - <<'AEGIS_PINNED_CYCLE_DEPLOY_735191'\n" + source + "\nAEGIS_PINNED_CYCLE_DEPLOY_735191"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subscription", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--ci-run-id", type=int, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    script = guest_script(args.commit)
    github_validation(args.commit, args.pr_number, args.ci_run_id)
    if not args.apply:
        print(json.dumps({"status": "validated_plan", "target": "aegis-wazuh",
                          "commit": args.commit, "new_resources": 0}))
        return
    print(invoke(args.subscription, "aegis-wazuh", script))


if __name__ == "__main__":
    main()
