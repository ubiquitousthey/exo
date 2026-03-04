# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

exo — Personal developer tooling monorepo. Houses reusable Claude Code skills, plugins, commands, scripts, GitHub Actions, project templates, and shared Python libraries.

## Repository Structure

```
exo/
├── .claude-plugin/plugin.json   — Plugin manifest (installable via `claude plugin add`)
├── skills/                      — Claude Code skills (SKILL.md per skill)
├── commands/                    — Claude Code slash commands (.md files)
├── agents/                      — Claude Code agent definitions (.md files)
├── hooks/hooks.json             — Claude Code hooks
├── .github/workflows/           — Reusable GitHub Actions workflows
├── .github/actions/             — Composite GitHub Actions
├── templates/                   — Project templates (copier format)
├── scripts/                     — Standalone utility scripts
├── lib/                         — Shared Python library (exo)
├── pyproject.toml               — Root dev tooling config (ruff)
└── CLAUDE.md
```

## Build & Run

```bash
# Lint
ruff check .

# Format
ruff format .

# Install shared library (editable)
pip install -e ./lib
```

## Conventions

### Adding a skill
Create `skills/<skill-name>/SKILL.md` with YAML frontmatter (`name`, `description`) followed by the skill body. Skills must be project-agnostic.

### Adding a command
Create `commands/<command-name>.md`. The filename (without extension) becomes the slash command name.

### Adding an agent
Create `agents/<agent-name>.md` with agent instructions.

### Adding a GitHub Action
- Reusable workflows go in `.github/workflows/`
- Composite actions go in `.github/actions/<action-name>/action.yml`

### Adding a template
Create a directory under `templates/` following [copier](https://copier.readthedocs.io/) conventions.

## How Other Projects Consume Assets

| Asset | How to use |
|-------|-----------|
| Skills, commands, agents | `claude plugin add /path/to/exo` |
| GitHub Actions | `uses: ubiquitousthey/exo/.github/workflows/file.yml@main` |
| Templates | `copier copy gh:ubiquitousthey/exo/templates/<name> ./dest` |
| Python library | `pip install -e /path/to/exo/lib` |

## Code Style

- Python 3.12+
- Ruff for linting and formatting (config in root `pyproject.toml`)
- Line length: 100
- Lint rules: E, F, I, N, UP, B, SIM, RUF
