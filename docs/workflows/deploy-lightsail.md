# Deploy site

**YAML:** [`.github/workflows/deploy-lightsail.yml`](../../.github/workflows/deploy-lightsail.yml)

**Secrets:** `LIGHTSAIL_HOST` (`54.232.149.254`), `LIGHTSAIL_SSH_KEY` (the `stephan-deploy` private key).

Pushing `frontend/**` or `backend/**` to `main` builds the site and copies it to the São Paulo instance. `/opt/stephan/debt.txt` stays on the server, except `BLOCKWALL_KEY`, which is written from the Actions secret so visitors see the maintenance page.
