# Navigation for agents

| Path | What it is |
|------|------------|
| `frontend/src/app/app.routes.ts` | Public routes. `/studio` is hidden from the header. |
| `frontend/src/app/core/api.service.ts` | The only HTTP client. Base URL is `environment.apiUrl`. |
| `frontend/src/environments/` | Dev points at `localhost:8000`. Production is generated. |
| `backend/app/main.py` | App factory, `/health`, `/api/v1/status`. |
| `backend/app/api/v1/contact.py` | Contact form. Writes `backend/data/messages.jsonl`. |
| `backend/app/api/v1/studio.py` | Studio gate and issue creation. |
| `.cursor/skills/studio-mode/SKILL.md` | Required when a public page, its copy, or its layout changes. `/studio` frames the live site and must be updated in that same change. |
| `frontend/src/app/features/company/` | Company portal at `/empresa`. Header Login. |
| `frontend/src/app/features/billing/` | Signup at `/cadastro`. The header register link lands here. The monthly fee follows how many forms the cycle covers, so signup does not choose a plan or a payment method. Supplier facts stay in `offer.config.ts`. |
| `backend/app/api/v1/orders.py` | Stores a signup in `backend/data/orders.jsonl` and sends the confirmation email. Does not charge. No card fields. No plan is chosen on signup. The access stays closed until `/confirmar` opens it. |
| `backend/app/api/v1/cnpj.py` | Public CNPJ lookup for `/cadastro`. Fills company and address. Does not return partners or store the number. |
| `backend/app/api/v1/company.py` | Company login, confirmation, and password reset. `internal` and `hse-it` do not share invitations. Those two accounts are already confirmed. |
| `frontend/src/app/features/account/` | `/confirmar` opens a signup from the email link. `/senha` asks for a reset and, with `?t=`, stores the new password. |
| `backend/app/db/schema.sql` | PostgreSQL schema for the HSE campaign. |
| `docs/TOOL.md` | `/tool` campaign: anonymity, upload formats, local and Lightsail PostgreSQL. |
| `docs/COMPANY_PORTAL.md` | Demo account, simulated forms, and the plan for real data. |
| `backend/app/core/config.py` | Settings from `debt.txt` / `backend/.env`. |
| `netlify.toml` | Frontend build and `/api/v1` proxy. |
| `render.yaml` | API service. |
| `.github/workflows/` | Lightsail deploy, Render deploy hook, weekly law report, issue solver. |
| `docs/NFSE.md` | National service invoice: tags, Simples Nacional, Fator R, and what emission still needs. |
| `docs/research/` | Destination for `[POST]` briefings. |

Public copy lives in `frontend/src/app/core/i18n/messages.ts`. Do not invent the partners' names.
