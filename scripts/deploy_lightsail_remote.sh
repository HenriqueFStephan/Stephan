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
