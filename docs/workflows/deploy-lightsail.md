# Deploy site

**YAML:** [`.github/workflows/deploy-lightsail.yml`](../../.github/workflows/deploy-lightsail.yml)

**Secrets:** `LIGHTSAIL_HOST` (`54.232.149.254`), `LIGHTSAIL_SSH_KEY` (the `stephan-deploy` private key).

Pushing `frontend/**` or `backend/**` to `main` builds the site and copies it to the São Paulo instance. The same job runs `scripts/postgres_on_lightsail.sh`, which installs PostgreSQL on that machine if it is missing and writes `DATABASE_URL` into `/opt/stephan/debt.txt` only when that key is absent. The rest of `/opt/stephan/debt.txt` stays, except `BLOCKWALL_KEY`, which is written from the Actions secret so visitors see the maintenance page.
