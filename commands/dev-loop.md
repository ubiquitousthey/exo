# /dev-loop

Autonomous issue-to-PR development loop. Picks up a GitHub issue, plans, implements, tests, and submits a PR.

## Usage

```
/dev-loop [--repo owner/repo] [--issue 42]
```

## Arguments

- `--repo owner/repo` — Target repository. Defaults to the current repo.
- `--issue N` — Work on a specific issue number. If omitted, picks the oldest open issue labeled `claude-ready`.

## Behavior

Parse the arguments from `$ARGUMENTS` and hand off to the **dev-loop agent** with the following context:

1. If `--repo` is provided, pass it as the target repository.
2. If `--issue` is provided, pass it as the target issue number.
3. Invoke the dev-loop agent to execute its full 10-step workflow.

The dev-loop agent will:
1. Pick or fetch the specified GitHub issue
2. Create a branch and draft PR
3. Write BDD test specifications
4. Plan implementation with nano-spec
5. Implement in phases with JIT testing
6. Automate BDD tests
7. Run and fix tests
8. Run the full test suite
9. Self-review the PR
10. Submit for human review

## Prerequisites

- `gh` CLI must be authenticated (`gh auth status`)
- Repository must have GitHub Issues enabled
- Issues should be labeled `claude-ready` (or use `--issue` to target a specific one)

## Labels

| Label | Meaning |
|-------|---------|
| `claude-ready` | Issue is ready for dev-loop to pick up |
| `dev-loop-active` | Dev-loop is currently working on this issue |
| `dev-loop-review` | Dev-loop finished, PR awaits human review |
