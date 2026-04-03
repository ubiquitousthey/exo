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

## Skills

Skills are self-contained capabilities that can be invoked independently or composed by agents. Each skill lives in `skills/<name>/SKILL.md`.

### Dev-loop pipeline

The **dev-loop** agent orchestrates these skills into an end-to-end issue-to-PR pipeline. Each skill can also be used standalone.

| Skill | Step | Description |
|-------|------|-------------|
| [`issue-pick`](skills/issue-pick/SKILL.md) | 1 | Find, claim, and complete GitHub issues labeled for automated development |
| [`nano-spec`](skills/nano-spec/SKILL.md) | 2 | Create and manage lightweight task specifications (README, todo, doc, log) |
| [`branch-pr`](skills/branch-pr/SKILL.md) | 3 | Create a git branch and draft PR from issue context |
| [`bdd-author`](skills/bdd-author/SKILL.md) | 4, 8 | Write BDD feature files from issue content and generate step definitions |
| [`ui-design`](skills/ui-design/SKILL.md) | 5 | Detect if a feature needs UI work and orchestrate superdesign generation |
| [`review-gate`](skills/review-gate/SKILL.md) | Gate | Post plan and BDD spec as a PR comment for human review |
| [`implement-phases`](skills/implement-phases/SKILL.md) | 6 | Execute nano-spec phases with research, coding, JIT testing, and commits |
| [`jit-test`](skills/jit-test/SKILL.md) | 6c | Generate bespoke tests for pending changes; promote durable tests to permanent suite |
| [`ui-verify`](skills/ui-verify/SKILL.md) | 7 | Static template audit + visual fidelity comparison against designs |
| [`test-loop`](skills/test-loop/SKILL.md) | 9, 10 | BDD test fix loop and full test suite with regression fixes |
| [`code-review`](skills/code-review/SKILL.md) | 11 | Self-review own PR or review any PR by number |
| [`showboat-proof`](skills/showboat-proof/SKILL.md) | 12 | Generate executable proof documents demonstrating features work |
| [`submit-pr`](skills/submit-pr/SKILL.md) | 13 | Finalize PR with traceability, test results, and proof links |

### Other skills

| Skill | Description |
|-------|-------------|
| [`req-decompose`](skills/req-decompose/SKILL.md) | Decompose requirements into implementable GitHub issues |

## Agents

Agents are autonomous multi-step workflows. Skills do the work; agents coordinate them. Each agent lives in `agents/<name>.md`.

| Agent | Description |
|-------|-------------|
| [`dev-loop`](agents/dev-loop.md) | End-to-end issue-to-PR pipeline — picks an issue, plans, implements, tests, reviews, and submits |
| [`self-review`](agents/self-review.md) | Reviews a PR diff for security, readability, architecture, and best practices |
| [`jit-test`](agents/jit-test.md) | Generates bespoke tests for pending code changes before commit |

The `self-review` and `jit-test` agents are also available as skills (`code-review` and `jit-test`) for use in the dev-loop pipeline and standalone invocation.

## Commands

Commands are slash-command entry points that parse arguments and delegate to agents or skills.

| Command | Description |
|---------|-------------|
| `/dev-loop` | Autonomous issue-to-PR loop with optional `--review-plan` for human checkpoints |
| `/ui-audit` | Run static template analysis for design system compliance |
| `/showboat-proof` | Generate executable proof documents |

## Dev-loop workflow

The dev-loop agent drives features from issue to PR in 13 steps, with every step backed by a standalone skill:

```
Issue ─── Plan ─── Branch ─── BDD Spec ─── UI Design
                                               │
                                          Review Gate
                                               │
Implement ─── UI Verify ─── Automate BDD ─── Test Loop (BDD)
                                                  │
                                    Test Loop (Full) ─── Code Review
                                                            │
                                                   Proof ─── Submit PR
```

**Planning (steps 1-5):** Pick issue, create nano-spec plan, branch + draft PR, write BDD spec, generate UI designs (if needed), then pause at a review gate for human approval.

**Implementation (steps 6-13):** Implement in phases with JIT testing (promoting durable tests), verify UI fidelity, automate and run BDD tests, run the full test suite, code review, generate proof, and submit the PR.

Use `--review-plan` to pause after planning for human review before implementation begins.

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

Includes the `exo.template_auditor` module used by the `ui-verify` skill for static HTML template analysis.
