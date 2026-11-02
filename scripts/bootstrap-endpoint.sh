#!/usr/bin/env bash
set -euo pipefail
umask 077
mkdir -p /var/lib/aegislake/evidence /var/lib/aegislake/monitored /var/lib/aegislake/normal
touch /var/log/aegislake-bootstrap.log
chmod 600 /var/log/aegislake-bootstrap.log
exec >>/var/log/aegislake-bootstrap.log 2>&1
trap 'date -u +%FT%TZ > /var/lib/aegislake/evidence/bootstrap.failed' ERR
export DEBIAN_FRONTEND=noninteractive
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  printf '/swapfile none swap sw 0 0\n' >> /etc/fstab
fi
if [ -f /usr/share/keyrings/wazuh.gpg ]; then chmod 644 /usr/share/keyrings/wazuh.gpg; fi
apt-get update -qq
apt-get install -y -qq curl ca-certificates gnupg rsyslog auditd
curl -fsSL https://packages.wazuh.com/key/GPG-KEY-WAZUH | gpg --batch --yes --dearmor -o /usr/share/keyrings/wazuh.gpg
chmod 644 /usr/share/keyrings/wazuh.gpg
printf 'deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main\n' > /etc/apt/sources.list.d/wazuh.list
apt-get update -qq
WAZUH_MANAGER='10.77.0.4' WAZUH_AGENT_NAME='aegis-endpoint' apt-get install -y -qq wazuh-agent=4.14.9-1
printf 'AegisLake controlled FIM baseline\n' > /var/lib/aegislake/monitored/marker.txt
python3 - <<'PY'
from pathlib import Path
p=Path("/var/ossec/etc/ossec.conf")
text=p.read_text()
entry='    <directories check_all="yes" realtime="yes">/var/lib/aegislake/monitored</directories>\n'
if entry not in text:
    if "</syscheck>" not in text:
        raise RuntimeError("Missing syscheck configuration")
    p.write_text(text.replace("</syscheck>",entry+"  </syscheck>",1))
PY
systemctl enable --now rsyslog auditd wazuh-agent
cat > /usr/local/sbin/aegis-normal <<'SH'
#!/usr/bin/env bash
set -euo pipefail
id >/dev/null
df -P / >/dev/null
date -u +%FT%TZ >> /var/lib/aegislake/normal/heartbeat.log
SH
chmod 750 /usr/local/sbin/aegis-normal
cat > /etc/systemd/system/aegis-normal.service <<'UNIT'
[Unit]
Description=AegisLake harmless baseline activity
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/aegis-normal
UNIT
cat > /etc/systemd/system/aegis-normal.timer <<'UNIT'
[Unit]
Description=AegisLake baseline every fifteen minutes
[Timer]
OnBootSec=5min
OnUnitActiveSec=15min
[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now aegis-normal.timer
date -u +%FT%TZ > /var/lib/aegislake/evidence/bootstrap.ok
