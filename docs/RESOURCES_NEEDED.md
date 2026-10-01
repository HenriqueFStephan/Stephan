# Resources you still have to create

Nothing below was copied from the other repository. Each value is new for this project.

## GitHub Actions secrets

| Secret | Where to get it | Where it goes |
|--------|-----------------|---------------|
| `CURSOR_API_KEY` | [Cursor Dashboard → Integrations](https://cursor.com/dashboard?tab=integrations) | GitHub → repo → Settings → Secrets → Actions |
| `RENDER_DEPLOY_HOOK_URL` | Render → `stephan-api` → Settings → Deploy Hook | Same Actions secrets list |
| Cursor GitHub App | Same Cursor integrations tab, installed on `Stephan` | No env var |

## Studio (hidden `/studio`)

| Variable | Where to get it | Where to put it |
|----------|-----------------|-----------------|
| `GITHUB_REPO` | `HenriqueFStephan/Stephan` once the repo exists | `debt.txt` locally and Render |
| `GITHUB_STUDIO_TOKEN` | GitHub → Settings → Developer settings → Fine-grained PAT. This repo only. Permissions: **Issues** read/write, **Contents** read/write (snips go to branch `studio-attachments`). | `debt.txt` and Render. Never in the Angular app. |
| `STUDIO_ACCESS_TOKEN` | A long random string you invent. This is the gate password, not the GitHub PAT. | `debt.txt` and Render. You type it on `/studio` in production. |

On `localhost` the gate is open and issue creation is a dry-run until the GitHub token exists.

## Render environment (blueprint already lists the keys)

Typed in the Render dashboard because `render.yaml` marks them `sync: false`:

- `SMTP_USERNAME`, `SMTP_FROM`, `SMTP_PASSWORD`, `CONSULTING_NOTIFY_TO` — only when you want email. A Gmail app password works with `smtp.gmail.com` port `587`.
- `GITHUB_STUDIO_TOKEN`
- `STUDIO_ACCESS_TOKEN`
- `BLOCKWALL_KEY` — same value as in `debt.txt`. While it is set, the public site shows the maintenance page. Leave it empty to take the wall down for everyone.

Also confirm after the first Netlify deploy:

- `FRONTEND_URL` equals the Netlify origin

## Campaign database

`DATABASE_URL` is PostgreSQL on the same machine as the API, host `127.0.0.1`. It is not a Render key and not a Lightsail managed database. Locally, use the Docker URL in `docs/TOOL.md` and put it in `debt.txt`. On the server, `scripts/postgres_on_lightsail.sh` writes it into `/opt/stephan/debt.txt`. If creating a database would open a payment screen, stop.

## Optional later

- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` if a future agent calls an LLM directly. The weekly report uses `CURSOR_API_KEY` in Actions, not these keys.
- Domain and SSL when you leave the `*.netlify.app` hostname.

## Checklist

- [ ] GitHub repo `HenriqueFStephan/Stephan` and a push of `main`
- [ ] Render blueprint applied; `/health` returns ok
- [ ] Netlify site; home card shows the API connection
- [ ] `FRONTEND_URL` matches the Netlify origin
- [ ] `RENDER_DEPLOY_HOOK_URL` and `CURSOR_API_KEY` in Actions secrets
- [ ] Cursor GitHub App installed on this repo
- [ ] `GITHUB_STUDIO_TOKEN` and `STUDIO_ACCESS_TOKEN` in `debt.txt` and on Render
