# Deploy — steps that need your accounts

The agent cannot log into GitHub, Render, or Netlify, and it must not copy tokens from another project.

## 1. Create the GitHub repository

1. Open https://github.com/new
2. Name: `SobralPsico` (owner `HenriqueFStephan`, so the slug matches `render.yaml`)
3. Do not add a README
4. From this folder:

```powershell
git init
git add .
git commit -m "Initial shell: frontend, backend, studio, and deploy wiring"
git branch -M main
git remote add origin https://github.com/HenriqueFStephan/SobralPsico.git
git push -u origin main
```

Use a GitHub personal access token if Git asks for a password.

## 2. Deploy the API on Render

1. https://dashboard.render.com → **New +** → **Blueprint**
2. Select `SobralPsico`. Render reads `render.yaml`.
3. When it asks for secrets (`sync: false`), paste them. You can leave SMTP blank for now. Studio tokens are in the next section.
4. Wait for the deploy. Open `https://sobralpsico-api.onrender.com/health`.
5. If Render assigned a different hostname, copy it. You will need it in step 3.

## 3. Deploy the site on Netlify

1. https://app.netlify.com → **Add new site** → **Import** from GitHub → `SobralPsico`
2. Netlify should read `netlify.toml`:

   | Field | Value |
   |-------|--------|
   | Base | `frontend` |
   | Build | `npm ci && npm run build:ci` |
   | Publish | `frontend/dist/sobralpsico` |

3. Environment variable before the first build:

   | Key | Value |
   |-----|--------|
   | `NG_APP_API_URL` | `/api/v1` |

4. If the Render URL is not `https://sobralpsico-api.onrender.com`, edit the proxy in `netlify.toml` and push.
5. Optional: rename the site to `sobralpsico` so the origin is `https://sobralpsico.netlify.app`.

## 4. Point CORS at the real site

Render → `sobralpsico-api` → **Environment** → `FRONTEND_URL` = the Netlify origin, no trailing slash. Save so Render redeploys.

If the Netlify name is not `sobralpsico`, also update `LIVE_FRONTEND_ORIGINS` in `backend/app/core/cors.py`.

## 5. Deploy hook

Render → `sobralpsico-api` → **Settings** → **Deploy Hook** → copy the URL.

GitHub → `SobralPsico` → **Settings** → **Secrets and variables** → **Actions** → New secret:

| Secret | Value |
|--------|--------|
| `RENDER_DEPLOY_HOOK_URL` | the deploy hook URL |
| `CURSOR_API_KEY` | from https://cursor.com/dashboard?tab=integrations |

`GITHUB_TOKEN` is provided by Actions. Do not create it.

Install the Cursor GitHub App on this repository from the same integrations page. Without it, the weekly report and the issue solver cannot open cloud agents.

## 6. Check

Open the Netlify URL. The home card should say the connection is ok. `/studio` should load the same page inside a frame with the note panel (localhost skips the gate; production asks for `STUDIO_ACCESS_TOKEN`).
