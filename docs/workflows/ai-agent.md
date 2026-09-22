# AI agent

**YAML:** [`.github/workflows/cursor-issue-solver.yml`](../../.github/workflows/cursor-issue-solver.yml)

**Script:** [`scripts/run_issue_solver_agents.py`](../../scripts/run_issue_solver_agents.py)

**Secrets:** `CURSOR_API_KEY`, and `GITHUB_TOKEN` (provided by Actions)

| Trigger | Fires when | What the agent does |
|---------|------------|---------------------|
| `solve` | Issue labeled `solve` | Implements the issue. Skips issues labeled `research` or `law-research`. |
| `correction` | Comment starts with `[CORRECTION]` | Applies that comment only. |
| `post` | Comment starts with `[POST]` on a `law-research` issue | Writes a Portuguese briefing in `docs/research/` for the named source. |

Complexity 1–3 is merged to the base branch. Complexity 4–5 opens a pull request.

The Cursor GitHub App must be installed on this repository or the launch fails.
