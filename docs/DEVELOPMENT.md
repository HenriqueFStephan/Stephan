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

## Where to add the questionnaire later

- New route next to `frontend/src/app/app.routes.ts`
- New router under `backend/app/api/v1/`, included from `backend/app/main.py`
- Call it from `frontend/src/app/core/api.service.ts`
