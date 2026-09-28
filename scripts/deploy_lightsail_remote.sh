#!/bin/bash
# Runs on the Lightsail instance. Uploads land in /tmp first.
set -euxo pipefail

find /var/www/stephan -mindepth 1 -delete
tar -xzf /tmp/site.tgz -C /var/www/stephan
tar -xzf /tmp/api.tgz -C /opt/stephan
/opt/stephan/venv/bin/pip install -r /opt/stephan/backend/requirements.txt
mkdir -p /opt/stephan/backend/data
chown -R www-data:www-data /var/www/stephan /opt/stephan/backend/data
systemctl restart stephan-api
systemctl reload nginx
curl -sf http://127.0.0.1:8000/health
rm -f /tmp/site.tgz /tmp/api.tgz /tmp/deploy_lightsail_remote.sh
