# Sobral Psico

Anonymous employee welfare questionnaire. This repository is the empty shell: Angular frontend, FastAPI backend, Netlify, Render, and the same GitHub Actions shape as the sibling project.

The home page only checks that the browser can reach `GET /api/v1/status`. Product copy and the questionnaire are not written yet.

The creative overlay lives at `/studio` (not in the public menu). On localhost it opens without a token. Sending an issue is a dry-run until `GITHUB_STUDIO_TOKEN` is set.

## Run locally

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

```powershell
cd frontend
npm install
npm start
```

Open http://localhost:4200 and http://localhost:4200/studio.

Copy `debt.txt.example` to `debt.txt` when you have tokens. The file is gitignored.

## Deploy

See [docs/DEPLOY.md](docs/DEPLOY.md) and [docs/RESOURCES_NEEDED.md](docs/RESOURCES_NEEDED.md). Those steps need your GitHub, Render, and Netlify accounts.
