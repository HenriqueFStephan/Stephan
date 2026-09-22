# Workflow notes

| Workflow | What it does | Secret |
|----------|----------------|--------|
| [Deploy backend](./deploy-backend.md) | POSTs the Render deploy hook when `backend/**` lands on `main` | `RENDER_DEPLOY_HOOK_URL` |
| [Weekly law report](./weekly-law-report.md) | Opens a GitHub issue of recent NR-1 and questionnaire sources | `CURSOR_API_KEY` |
| [AI agent](./ai-agent.md) | Cloud agent for `solve`, `[CORRECTION]`, and `[POST]` | `CURSOR_API_KEY` |

`/studio` files an issue **without** `solve`. Add that label on GitHub when you want the agent to run.

A comment that starts with `[POST]` on an issue labeled `law-research` asks the agent to write a briefing in `docs/research/`.
