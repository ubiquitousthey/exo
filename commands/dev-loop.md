# /dev-loop

Autonomous issue-to-PR development loop. Picks up a GitHub issue, plans, implements, tests, and submits a PR.

## Usage

```
/dev-loop [--repo owner/repo] [--issue 42] [--review-plan]
```

## Arguments

- `--repo owner/repo` — Target repository. Defaults to the current repo.
- `--issue N` — Work on a specific issue number. If omitted, picks the oldest open issue labeled `claude-ready`.
- `--review-plan` — Pause after planning and UI design (step 5) so the user can review the plan before implementation begins.

## Behavior

Parse the arguments from `$ARGUMENTS` and hand off to the **dev-loop agent**.

### Without `--review-plan` (default — full autonomous run)

1. If `--repo` is provided, pass it as the target repository.
2. If `--issue` is provided, pass it as the target issue number.
3. Invoke the dev-loop agent to execute its full workflow.

### With `--review-plan` (pause for human review)

1. Parse `--repo` and `--issue` as above.
2. Invoke the dev-loop agent with `--plan-only` added to the arguments. This runs steps 1-5 only (pick issue, create branch, write BDD spec, create nano-spec plan, generate UI designs if needed) and then stops.
3. When the agent returns, present the plan to the user:
   - Show the issue title and number
   - Show the nano-spec task directory path (`tasks/dev-loop-<issue-number>/`)
   - Tell the user: "The plan is ready for review. Key files: `tasks/dev-loop-<N>/doc.md` (decisions), `tasks/dev-loop-<N>/todo.md` (implementation phases), the BDD feature file, and any UI designs in `.superdesign/design_iterations/`."
   - Ask: "Review the plan and let me know when you're ready to proceed, or tell me what to change."
4. **Wait for the user's response.** Do NOT proceed automatically.
   - If the user says to proceed (e.g., "go", "looks good", "implement it"), invoke the dev-loop agent with `--implement-only --issue <N>` (plus `--repo` if provided). This runs steps 6-12.
   - If the user requests changes, make the changes to the nano-spec files, then ask again if they're ready to proceed.
   - If the user says to stop, report status and stop.

## The dev-loop agent will:

**Steps 1-5 (planning — run with `--plan-only`):**
1. Pick or fetch the specified GitHub issue
2. Plan implementation with nano-spec
3. Create a branch and draft PR
4. Write BDD test specifications
5. Generate UI designs with superdesign (if the feature involves UI)

**Steps 6-12 (implementation — run with `--implement-only`):**
6. Implement in phases with JIT testing
7. Automate BDD tests
8. Run and fix tests
9. Run the full test suite
10. Self-review the PR
11. Generate proof
12. Submit for human review

## Prerequisites

- `gh` CLI must be authenticated (`gh auth status`)
- Repository must have GitHub Issues enabled
- Issues should be labeled `claude-ready` (or use `--issue` to target a specific one)

## Labels

| Label | Meaning |
|-------|---------|
| `claude-ready` | Issue is ready for dev-loop to pick up |
| `dev-loop-active` | Dev-loop is currently working on this issue |
| `dev-loop-review-gate` | PR is paused at review gate, awaiting human review of plan and BDD spec |
| `dev-loop-review` | Dev-loop finished, PR awaits human review |
