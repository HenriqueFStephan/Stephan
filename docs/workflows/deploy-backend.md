# Deploy backend

**YAML:** [`.github/workflows/deploy-backend.yml`](../../.github/workflows/deploy-backend.yml)

**Secret:** `RENDER_DEPLOY_HOOK_URL` from Render → `stephan-api` → Settings → Deploy Hook.

Pushing `backend/**` to `main` POSTs that hook. If the secret is missing, the job warns and exits 0.
