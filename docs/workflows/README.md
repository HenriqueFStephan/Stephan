# Workflow notes

| Workflow | What it does | Secret |
|----------|----------------|--------|
| [Deploy site](./deploy-lightsail.md) | Builds the site and copies it to Lightsail when `frontend/**` or `backend/**` lands on `main` | `LIGHTSAIL_HOST`, `LIGHTSAIL_SSH_KEY` |
| [Deploy backend](./deploy-backend.md) | POSTs the Render deploy hook when `backend/**` lands on `main` | `RENDER_DEPLOY_HOOK_URL` |
| [Weekly law report](./weekly-law-report.md) | Opens a GitHub issue of recent NR-1 and questionnaire sources | `CURSOR_API_KEY` |
| [AI agent](./ai-agent.md) | Cloud agent for `solve`, `[CORRECTION]`, and `[POST]` | `CURSOR_API_KEY` |

`/studio` files an issue with the `solve` label, so the agent runs when the token is configured.

A comment that starts with `[POST]` on an issue labeled `law-research` asks the agent to write a briefing in `docs/research/`.
