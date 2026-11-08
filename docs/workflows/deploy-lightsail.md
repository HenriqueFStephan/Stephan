# Deploy site

**YAML:** [`.github/workflows/deploy-lightsail.yml`](../../.github/workflows/deploy-lightsail.yml)

**Secrets:** `LIGHTSAIL_HOST` (`54.232.149.254`), `LIGHTSAIL_SSH_KEY` (the `stephan-deploy` private key).

Pushing `frontend/**` or `backend/**` to `main` builds the site and copies it to the São Paulo instance. The job first writes a backup under `/var/backups/stephan` (the database dump plus `messages.jsonl` and `orders.jsonl`, kept 14 days, mode 600) and installs the same backup on a daily cron. It then runs `scripts/postgres_on_lightsail.sh`, which installs PostgreSQL on that machine only when it is missing and writes `DATABASE_URL` into `/opt/stephan/debt.txt` only when that key is absent. A PostgreSQL that is already listening on localhost is not upgraded and not restarted. The rest of `/opt/stephan/debt.txt` stays.
