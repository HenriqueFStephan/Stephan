#!/bin/bash
# Runs on the Lightsail instance. Uploads land in /tmp first.
set -euxo pipefail

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
rm -f /tmp/site.tgz /tmp/api.tgz /tmp/deploy_lightsail_remote.sh /tmp/postgres_on_lightsail.sh
