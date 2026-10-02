# Development

## Prerequisites

- Node.js 18
- Python 3.11+
- npm 8+

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Docs: http://localhost:8000/docs

Tests: `pytest` from `backend/`.

## Frontend

```powershell
cd frontend
npm install
npm start
```

App: http://localhost:4200

`/studio` is the local creative overlay. It is not linked from the header.

## Environment

Copy `debt.txt.example` to `debt.txt` at the repo root. The API also reads `backend/.env`. Both are gitignored.

## Campaign database

The HSE invitation list uses PostgreSQL on this machine, not a hosted database. Full rules: [TOOL.md](TOOL.md).

```powershell
docker compose up -d db
```

If Docker is not installed:

```powershell
python scripts/postgres_local.py
```

Either way the server listens on `127.0.0.1:5432` only. Put this in `debt.txt` and restart the API:

```
DATABASE_URL=postgresql://stephan:stephan@127.0.0.1:5432/stephan
```

The password above is the local Docker default. The Lightsail password is different and stays in `/opt/stephan/debt.txt`.

## Questionnaire on `/tool`

The campaign form is already `/tool?t=`. After the introduction comes Anexo B, then the 35 HSE-IT items. Anexo B is stored on `hse_responses`, not on the invitation. See [TOOL.md](TOOL.md). Do not add `/tool` to the header or the footer.
