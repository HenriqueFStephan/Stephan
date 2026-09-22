---
name: project-navigation
description: Map of the Sobral Psico shell. Use when adding a route, an API, or a workflow.
---

# Project navigation

Read `docs/AGENT_NAVIGATION.md` and `docs/ARCHITECTURE.md` before adding modules.

- Public UI routes go in `frontend/src/app/app.routes.ts`.
- HTTP calls go through `frontend/src/app/core/api.service.ts`.
- API routers go in `backend/app/api/v1/` and are included from `backend/app/main.py`.
- `/studio` is the hidden issue composer. Do not link it in the header.
- Do not put tokens in the frontend. Studio secrets stay in `debt.txt` and Render.
