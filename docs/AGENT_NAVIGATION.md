# Navigation for agents

| Path | What it is |
|------|------------|
| `frontend/src/app/app.routes.ts` | Public routes. `/studio` is hidden from the header. |
| `frontend/src/app/core/api.service.ts` | The only HTTP client. Base URL is `environment.apiUrl`. |
| `frontend/src/environments/` | Dev points at `localhost:8000`. Production is generated. |
| `backend/app/main.py` | App factory, `/health`, `/api/v1/status`. |
| `backend/app/api/v1/contact.py` | Contact form. Writes `backend/data/messages.jsonl`. |
| `backend/app/api/v1/studio.py` | Studio gate and issue creation. |
| `backend/app/api/v1/blockwall.py` | Maintenance wall. On while `BLOCKWALL_KEY` is set. |
| `frontend/src/app/features/company/` | Company portal at `/empresa`. Footer link, not the header. |
| `backend/app/api/v1/company.py` | Company login. `internal` and `hse-it` do not share invitations. |
| `backend/app/db/schema.sql` | PostgreSQL schema for the HSE campaign. |
| `docs/TOOL.md` | `/tool` campaign: anonymity, upload formats, local and Lightsail PostgreSQL. |
| `docs/COMPANY_PORTAL.md` | Demo account, simulated forms, and the plan for real data. |
| `backend/app/core/config.py` | Settings from `debt.txt` / `backend/.env`. |
| `netlify.toml` | Frontend build and `/api/v1` proxy. |
| `render.yaml` | API service. |
| `.github/workflows/` | Lightsail deploy, Render deploy hook, weekly law report, issue solver. |
| `docs/research/` | Destination for `[POST]` briefings. |

Public copy lives in `frontend/src/app/core/i18n/messages.ts`. Do not invent the partners' names.
