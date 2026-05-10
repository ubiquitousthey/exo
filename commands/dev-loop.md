# /dev-loop

Autonomous issue-to-PR development loop. Picks up a GitHub issue, plans, implements, tests, and submits a PR.

## Usage

```
/dev-loop [--repo owner/repo] [--issue 42] [--review-plan]
```

## Arguments

- `--repo owner/repo` — Target repository. Defaults to the current repo.
- `--issue N` — Work on a specific issue number. If omitted, picks the oldest open issue labeled `claude-ready`.
- `--review-plan` — Pause after planning and UI design (step 6, before the Review Gate) so the user can review the realignment, plan, and BDD spec before implementation begins.

## Behavior

Parse the arguments from `$ARGUMENTS` and hand off to the **dev-loop agent**.

### Without `--review-plan` (default — full autonomous run)

1. If `--repo` is provided, pass it as the target repository.
2. If `--issue` is provided, pass it as the target issue number.
3. Invoke the dev-loop agent to execute its full workflow.

### With `--review-plan` (pause for human review)

1. Parse `--repo` and `--issue` as above.
2. Invoke the dev-loop agent with `--plan-only` added to the arguments. This runs steps 1-6 only (pick issue, realign with current system, plan with nano-spec, create branch and draft PR, write BDD spec, generate UI designs if needed) and then stops at the Review Gate.
3. When the agent returns, present the plan to the user:
   - Show the issue title and number
   - Show the realignment summary (drift detected, core need, what changed in the issue body)
   - Show the nano-spec task directory path (`tasks/<feature-slug>/`)
   - Tell the user: "The plan is ready for review. Key files: `tasks/<feature-slug>/doc.md` (decisions), `tasks/<feature-slug>/todo.md` (implementation phases), the BDD feature file, and any UI designs in `.superdesign/design_iterations/`. The realignment comment is on the GitHub issue."
   - Ask: "Review the plan and let me know when you're ready to proceed, or tell me what to change."
4. **Wait for the user's response.** Do NOT proceed automatically.
   - If the user says to proceed (e.g., "go", "looks good", "implement it"), invoke the dev-loop agent with `--implement-only --issue <N>` (plus `--repo` if provided). This runs steps 8-16.
   - If the user requests changes, make the changes to the nano-spec files, then ask again if they're ready to proceed.
   - If the user says to stop, report status and stop.

## The dev-loop agent will:

**Steps 1-6 (planning — run with `--plan-only`):**
1. Pick or fetch the specified GitHub issue
2. Realign the issue with the current system (rewrite issue body, post comment)
3. Plan implementation with nano-spec
4. Create a branch and draft PR
5. Write BDD test specifications (user-perspective scenarios)
6. Generate UI designs with superdesign (if the feature involves UI)

— Review Gate (Step 7) —

**Steps 8-16 (implementation — run with `--implement-only`):**
8. Implement in phases with JIT testing
9. UI fidelity check (static template audit + visual comparison)
10. Automate BDD tests (real entry points, observable assertions)
11. BDD guard (hard fail + auto-fix loop on user-perspective anti-patterns)
12. Run and fix BDD tests
13. Run the full test suite
14. Self-review the PR
15. Generate proof
16. Submit for human review

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
