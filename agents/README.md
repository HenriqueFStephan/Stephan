# Agents

The weekly law report and the issue solver run from `scripts/` inside GitHub Actions.
The `solve` prompt in `scripts/run_issue_solver_agents.py` always tells that agent to update `/studio` when a public page, its copy, or its layout changes. The steps are in `.cursor/skills/studio-mode/SKILL.md`.
This folder holds the source catalog (`data/discovered_sources.json`) and the reading list (`config/research_sources.yaml`).

`[POST]` briefings land in `docs/research/`.
