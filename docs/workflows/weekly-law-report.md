# Weekly law report

**YAML:** [`.github/workflows/weekly-law-research.yml`](../../.github/workflows/weekly-law-research.yml)

**Script:** [`scripts/run_weekly_law_research.py`](../../scripts/run_weekly_law_research.py)

**Secret:** `CURSOR_API_KEY`

Runs Mondays 06:30 UTC, or on demand. A Cursor cloud agent looks for official instruments and peer-reviewed sources from the past month about:

- NR-1 chapter 1.5 and Portaria MTE nº 1.419/2024 (psychosocial risks in the GRO/PGR)
- Later MTE portarias, the May 2026 enforcement window, and the MTE guide
- Anonymous workplace questionnaires, including the rule that a questionnaire is a method and is not mandatory by itself
- LGPD limits when answers can identify a worker
- Methods literature on work-related psychosocial risk

Accepted items become a GitHub issue titled `[RESEARCH] NR-1 Welfare {date}` with labels `law-research` and `research`. Those labels keep the issue solver from treating the digest as a coding task.

The catalog `agents/data/discovered_sources.json` starts empty. The workflow commits new entries so the next week skips them.

Comment `[POST]` plus the source name on that issue to file a briefing under `docs/research/`.
