# exo

Personal developer tooling monorepo. Centralizes reusable Claude Code skills, plugins, commands, scripts, GitHub Actions, project templates, and shared Python libraries.

## Install as a Claude Code plugin

```bash
claude plugin add /path/to/exo
```

This makes all skills, commands, and agents available in any project.

## Repository structure

| Directory | Purpose |
|-----------|---------|
| `skills/` | Claude Code skills (`SKILL.md` per skill) |
| `commands/` | Claude Code slash commands (`.md` files) |
| `agents/` | Claude Code agent definitions (`.md` files) |
| `hooks/` | Claude Code hooks (`hooks.json`) |
| `.github/workflows/` | Reusable GitHub Actions workflows |
| `.github/actions/` | Composite GitHub Actions |
| `templates/` | Project templates (copier format) |
| `scripts/` | Standalone utility scripts |
| `lib/` | Shared Python library (`exo`) |

## Use GitHub Actions

Reference reusable workflows from other repos:

```yaml
jobs:
  example:
    uses: ubiquitousthey/exo/.github/workflows/example.yml@main
```

## Scaffold from templates

```bash
copier copy gh:ubiquitousthey/exo/templates/python-app ./my-new-project
```

## Shared Python library

```bash
pip install -e ./lib
```
