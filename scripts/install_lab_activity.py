"""Install the lab activity timer using the signed-in Azure CLI operator.

Requires explicit VM Run Command rights for the two dedicated lab VMs.
The credit-guard identity deliberately has no such rights.
Only public SSH keys cross the Run Command response boundary.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess

GROUP = "rg-aegislake-lab"


def invoke(subscription, vm, source):
    if vm not in {"aegis-wazuh", "aegis-endpoint"}:
        raise ValueError("Only the dedicated lab VMs are supported")
    result = subprocess.run([
        "az", "vm", "run-command", "invoke", "--subscription", subscription,
        "-g", GROUP, "-n", vm, "--command-id", "RunShellScript",
        "--scripts", source, "-o", "json",
    ], capture_output=True, text=True, check=True, timeout=900)
    document = json.loads(result.stdout)
    messages = "\n".join(item["message"] for item in document["value"])
    if "[stderr]" not in messages or "[stdout]" not in messages:
        raise RuntimeError("Unexpected Run Command response")
    stdout = messages.split("[stdout]", 1)[1].split("[stderr]", 1)[0].strip()
    stderr = messages.split("[stderr]", 1)[1].strip()
    if stderr:
        raise RuntimeError("Guest command reported an error: " + stderr[:500])
    return stdout


def public_key(output):
    for line in output.splitlines():
        if re.fullmatch(r"ssh-ed25519 [A-Za-z0-9+/=]+(?: [^\r\n]*)?", line):
            return " ".join(line.split()[:2])
    raise ValueError("Missing Ed25519 public key")


def python_command(source):
    return "set -eu\npython3 - <<'AEGIS_INSTALL_ACTIVITY_695217'\n" + source + "\nAEGIS_INSTALL_ACTIVITY_695217"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subscription", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    endpoint_key = public_key(invoke(args.subscription, "aegis-endpoint",
                                     "set -eu\ncat /etc/ssh/ssh_host_ed25519_key.pub"))
    manager_key = public_key(invoke(args.subscription, "aegis-wazuh", python_command("""
import os
from pathlib import Path
import subprocess
os.umask(0o077)
config=Path('/etc/aegislake')
config.mkdir(parents=True,exist_ok=True)
key=config/'activity_ed25519'
if not key.exists():
    subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(key)],check=True)
print(key.with_suffix('.pub').read_text().strip())
""")))
    session = """#!/usr/bin/env bash
set -euo pipefail
case "${SSH_ORIGINAL_COMMAND:-}" in
  baseline)
    id >/dev/null
    df -P / >/dev/null
    printf '{"activity":"baseline","completed":true}\\n'
    ;;
  fim)
    date -u +%FT%TZ >> /var/lib/aegislake/monitored/marker.txt
    printf '{"activity":"fim","completed":true}\\n'
    ;;
  *) exit 64 ;;
esac
"""
    authorized = 'restrict,from="10.77.0.4",command="/usr/local/sbin/aegis-lab-session" ' + manager_key + "\n"
    endpoint_setup = """
import json,os,pwd,subprocess
from pathlib import Path
os.umask(0o077)
try:
    account=pwd.getpwnam('aegis-lab')
except KeyError:
    subprocess.run(['useradd','--create-home','--shell','/bin/bash','aegis-lab'],check=True)
    account=pwd.getpwnam('aegis-lab')
if account.pw_uid < 1000:
    raise RuntimeError('Unexpected existing lab account')
""" + "session=" + repr(session) + "\nauthorized=" + repr(authorized) + """
command=Path('/usr/local/sbin/aegis-lab-session')
command.write_text(session)
command.chmod(0o755)
ssh=Path(account.pw_dir)/'.ssh'
ssh.mkdir(exist_ok=True)
ssh.chmod(0o700)
os.chown(ssh,account.pw_uid,account.pw_gid)
keys=ssh/'authorized_keys'
keys.write_text(authorized)
keys.chmod(0o600)
os.chown(keys,account.pw_uid,account.pw_gid)
marker=Path('/var/lib/aegislake/monitored/marker.txt')
os.chown(marker,account.pw_uid,account.pw_gid)
marker.chmod(0o640)
# Permit traversal to this one monitored file; evidence subdirectories stay private.
for directory in [marker.parent.parent,marker.parent]:
    os.chown(directory,0,account.pw_gid)
    directory.chmod(0o710)
subprocess.run(['systemctl','enable','--now','ssh.socket'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
print('restricted-lab-account-ready')
"""
    print(invoke(args.subscription, "aegis-endpoint", python_command(endpoint_setup)))
    timer = """[Unit]
Description=Check AegisLake 48-hour activity cadence
[Timer]
OnBootSec=10min
OnUnitActiveSec=1h
AccuracySec=5min
[Install]
WantedBy=timers.target
"""
    unit = """[Unit]
Description=Bounded AegisLake SSH and FIM lab activity
After=network-online.target wazuh-manager.service
Wants=network-online.target
[Service]
Type=oneshot
UMask=0077
ExecStart=/opt/aegislake/.venv/bin/python /opt/aegislake/scripts/run_lab_activity.py
TimeoutStartSec=5min
"""
    files = {
        "/etc/aegislake/known_hosts": "10.77.0.5 " + endpoint_key + "\n",
        "/opt/aegislake/scripts/run_lab_activity.py": (root/"scripts/run_lab_activity.py").read_text(),
        "/opt/aegislake/src/aegislake/wazuh.py": (root/"src/aegislake/wazuh.py").read_text(),
        "/etc/systemd/system/aegis-activity.service": unit,
        "/etc/systemd/system/aegis-activity.timer": timer,
    }
    manager_setup = "files=" + repr(files) + """
import os,subprocess
from pathlib import Path
os.umask(0o077)
for name,content in files.items():
    path=Path(name)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(content)
    path.chmod(0o600)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now','aegis-activity.timer'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
subprocess.run(['systemctl','start','--no-block','aegis-activity.service'],check=True)
print('activity-timer-installed')
"""
    print(invoke(args.subscription, "aegis-wazuh", python_command(manager_setup)))


if __name__ == "__main__":
    main()
