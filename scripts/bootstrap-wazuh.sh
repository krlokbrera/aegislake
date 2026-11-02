#!/usr/bin/env bash
set -euo pipefail
umask 077
mkdir -p /var/lib/aegislake/evidence
touch /var/log/aegislake-bootstrap.log
chmod 600 /var/log/aegislake-bootstrap.log
exec >>/var/log/aegislake-bootstrap.log 2>&1
trap 'date -u +%FT%TZ > /var/lib/aegislake/evidence/bootstrap.failed' ERR
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq curl ca-certificates git python3-venv jq openssh-client
mkdir -p /root/wazuh-install
cd /root/wazuh-install
curl -fsSL https://packages.wazuh.com/4.14/wazuh-install.sh -o wazuh-install.sh
echo '20358b7dfc5b7fbb9b1ff62fec16a2922f6b553def99bf5aabdf6b3c3b4d9ddc  wazuh-install.sh' | sha256sum -c -
bash wazuh-install.sh -a
chmod 600 /var/log/aegislake-bootstrap.log
if [ -f wazuh-install-files.tar ]; then chmod 600 wazuh-install-files.tar; fi
git init -q /opt/aegislake
cd /opt/aegislake
git remote add origin https://github.com/krlokbrera/aegislake.git
git fetch -q --depth 1 origin 39017eef58148b1a41f8835550b8ca9c2f6509f4
git checkout -q --detach FETCH_HEAD
python3 -m venv /opt/aegislake/.venv
/opt/aegislake/.venv/bin/pip install --disable-pip-version-check -q .
mkdir -p /etc/aegislake /var/lib/aegislake/runs
date -u +%FT%TZ > /var/lib/aegislake/evidence/bootstrap.ok
