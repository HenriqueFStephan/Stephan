#!/bin/bash
# Runs on the Lightsail instance. Uploads land in /tmp first.
set -euxo pipefail

install -d -m 755 /opt/stephan/scripts
if [[ -f /tmp/backup_stephan.sh ]]; then
  install -m 700 /tmp/backup_stephan.sh /opt/stephan/scripts/backup_stephan.sh
  cat > /etc/cron.d/stephan-backup << 'EOF'
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
0 3 * * * root /opt/stephan/scripts/backup_stephan.sh >> /var/log/stephan-backup.log 2>&1
EOF
  chmod 644 /etc/cron.d/stephan-backup
fi

find /var/www/stephan -mindepth 1 -delete
tar -xzf /tmp/site.tgz -C /var/www/stephan
tar -xzf /tmp/api.tgz -C /opt/stephan
/opt/stephan/venv/bin/pip install -r /opt/stephan/backend/requirements.txt
mkdir -p /opt/stephan/backend/data
chown -R www-data:www-data /var/www/stephan /opt/stephan/backend/data
if [[ -f /tmp/wa.env ]]; then
  python3 - << 'PY'
from pathlib import Path

incoming = Path("/tmp/wa.env")
incoming.chmod(0o600)
raw = incoming.read_text(encoding="utf-8")
incoming.unlink()
updates = {}
for line in raw.splitlines():
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    if key in {"WHATSAPP_TOKEN", "WHATSAPP_PHONE_NUMBER_ID"} and value.strip():
        updates[key] = value
if len(updates) == 2:
    path = Path("/opt/stephan/debt.txt")
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = []
    seen = set()
    for line in text.splitlines():
        key = line.split("=", 1)[0] if line and not line.startswith("#") and "=" in line else None
        if key in updates:
            lines.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            lines.append(line)
    for key, value in updates.items():
        if key not in seen:
            lines.append(f"{key}={value}")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print("whatsapp settings written")
else:
    print("whatsapp settings skipped")
PY
fi
if [[ -f /opt/stephan/debt.txt ]]; then
  chown www-data:www-data /opt/stephan/debt.txt
  chmod 600 /opt/stephan/debt.txt
fi
systemctl restart stephan-api
systemctl reload nginx
for _ in 1 2 3 4 5 6 7 8 9 10; do
  curl -sf http://127.0.0.1:8000/health && break
  sleep 1
done
curl -sf http://127.0.0.1:8000/health
rm -f /tmp/site.tgz /tmp/api.tgz /tmp/deploy_lightsail_remote.sh /tmp/postgres_on_lightsail.sh /tmp/backup_stephan.sh
