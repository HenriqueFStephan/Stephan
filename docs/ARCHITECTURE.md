# Architecture

```
browser  →  Angular (Netlify)  →  /api/v1/* proxy  →  FastAPI (Render)
                                              ↘
                                               GitHub issues  (/studio)
```

| Piece | Role |
|-------|------|
| `frontend/` | Angular 16. `environment.apiUrl` is `http://localhost:8000/api/v1` in dev and `/api/v1` in production. `scripts/generate-env.js` writes the production file from `NG_APP_API_URL`. |
| `netlify.toml` | Builds `frontend`, publishes `dist/stephan`, proxies `/api/v1/*` to Render. |
| `backend/` | FastAPI. `GET /health` is the Render check. `GET /api/v1/status` is the same payload through the proxy. |
| `render.yaml` | Blueprint for `stephan-api`. Secrets use `sync: false`. |
| `/studio` | Hidden page. On localhost it skips the access token. With `GITHUB_STUDIO_TOKEN` it opens a GitHub issue labeled `solve` and stores snips on branch `studio-attachments`, in the same order as the composer. |
| `/empresa` | Company portal. Login stays on the API. `admin` is company `internal`; `artigo` is company `hse-it`. The charts are still a simulated wave; see `docs/COMPANY_PORTAL.md`. Invitations and answers are per company; see `docs/TOOL.md`. |
| `/tool` | Local reading with no token. With `?t=`, the campaign form for that invitation. |
| PostgreSQL | HSE campaign only. Same machine as the API, `127.0.0.1` only. `DATABASE_URL` in `debt.txt`. Not a Lightsail managed database. |
| `.github/workflows/` | Deploy hook, weekly law report, issue solver. |

CORS allows `FRONTEND_URL`, `http://localhost:4200`, and `https://stephan-psico.netlify.app`. Production traffic should stay same-origin via the Netlify proxy, so the browser does not need CORS for `/api/v1`.
