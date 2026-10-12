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

## Cadastro and payment

The pages are `/cadastro` and `/pagamento`. The header register link starts signup. The API stores the order in `backend/data/orders.jsonl` (gitignored, and it contains the signer CPF). It does not charge.

Public facts of the offer go in `frontend/src/app/features/billing/offer.config.ts`. Leave a field empty until it is real. The payment page lists whatever is still blank. Rebuild the site after editing the file.

| Field in `offer.config.ts` | What to put |
|----------------------------|-------------|
| `supplier.legalName` | Razão social, as on the CNPJ card |
| `supplier.cnpj` | CNPJ of the practice |
| `supplier.municipalRegistration` | Inscrição municipal, for the NFS-e |
| `supplier.street`, `number`, `complement`, `district`, `city`, `state`, `postalCode` | Physical address |
| `supplier.email` | Public email |
| `supplier.phone` | Public phone |
| `supplier.sacEmail` | Channel for service, withdrawal, and complaints. Can repeat `email` |
| `supplier.privacyEmail` | Channel for LGPD requests. Can repeat `email` |
| `supplier.councilRegistration` | Optional. CRP or other council id. Empty hides the line |
| `service.executionBusinessDays` | Business days to carry out the cycle after payment clears |
| `price.cents` | Price in cents. R$ 10,00 is `1000`. Null until you publish one |
| `price.issIncluded` | `true` if `cents` already contains ISS. `false` if ISS is added on top |
| `price.issRatePercent` | ISS rate of the supplier city, from the accountant. At most 5 |
| `card.maxInstallments` | Keep `1` for cash. Raise it only together with `totalsCents` |
| `card.totalsCents` | Total charged for that many installments, in cents. Index 0 unused. Do not leave the page to invent interest |

Do not put a gateway token in that file.

When you choose an institution authorized by the Central Bank (Pix participant, and a card checkout that keeps the card number off this server), add `PAYMENT_PROVIDER` and `PAYMENT_ACCESS_TOKEN` to `debt.txt` and to Render. The API does not read them yet: wiring the charge is a later change. Until then the button says the order is only recorded.

Also still outside the page, with the accountant and whoever reviews the contract: issuing the NFS-e, and confirming the cancellation sentence before a real charge.

The national service invoice is documented in `docs/NFSE.md`. The consultation portal only checks a note that already exists. Emission is the Emissor Nacional or the city's own system, with an e-CNPJ that never goes in the Angular app. Before the price line can tell the truth, the accountant still has to say: Simples regime (`regApTribSN`), whether Fator R is at or above 28% this month, the service codes (`cTribNac`, `cNBS`, and the city's `cTribMun`), and whether a company buyer withholds tax. The sample code `041601` is clinical psychology. Do not hard-code it onto this cycle until that choice is made.
