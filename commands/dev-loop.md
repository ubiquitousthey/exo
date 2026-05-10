# /dev-loop

Autonomous issue-to-PR development loop. Picks up a GitHub issue, plans, implements, tests, and submits a PR.

## Usage

```
/dev-loop [--repo owner/repo] [--issue 42] [--review-plan]
```

## Arguments

- `--repo owner/repo` — Target repository. Defaults to the current repo.
- `--issue N` — Work on a specific issue number. If omitted, picks the oldest open issue labeled `claude-ready`.
- `--review-plan` — Pause at the Review Gate (after step 10) so the user can review the realignment, triage, plan, BDD spec or reproduction test, UI designs, and answer the top-5 decisions interview before implementation begins.

## Behavior

Parse the arguments from `$ARGUMENTS` and hand off to the **dev-loop agent**.

### Without `--review-plan` (default — full autonomous run)

1. If `--repo` is provided, pass it as the target repository.
2. If `--issue` is provided, pass it as the target issue number.
3. Invoke the dev-loop agent to execute its full workflow.

### With `--review-plan` (pause for human review)

1. Parse `--repo` and `--issue` as above.
2. Invoke the dev-loop agent with `--plan-only` added to the arguments. This runs steps 1-10 (pick issue, realign with current system, triage, plan with nano-spec, create branch and draft PR, write BDD spec or bug reproduction test based on triage, generate UI designs if needed, formulate top-5 decisions interview, post the Review Gate) and then stops.
3. When the agent returns, present the plan to the user:
   - Show the issue title and number
   - Show the realignment summary (drift detected, core need, what changed in the issue body)
   - Show the triage track and flags
   - Show the nano-spec task directory path (`tasks/<feature-slug>/`)
   - Tell the user: "The plan is ready for review. Key files: `tasks/<feature-slug>/todo.md` (implementation phases), `tasks/<feature-slug>/doc.md` (decisions, on full plans), `tasks/<feature-slug>/interview.md` (the top-5 decisions posted at the gate), the BDD feature file or reproduction test, and any UI designs in `.superdesign/design_iterations/`. The Review Gate comment is on the PR."
   - Ask: "Answer the interview questions on the PR and let me know when you're ready to proceed, or tell me what to change."
4. **Wait for the user's response.** Do NOT proceed automatically.
   - If the user says to proceed (e.g., "go", "looks good", "implement it"), invoke the dev-loop agent with `--implement-only --issue <N>` (plus `--repo` if provided). This runs steps 11-20 (process interview reply, then implementation through submit).
   - If the user requests changes, make the changes to the nano-spec files, then ask again if they're ready to proceed.
   - If the user says to stop, report status and stop.

## The dev-loop agent will:

Many steps are conditional on the triage track (feature / bug / refactor / chore / spike) and its flag set. Steps marked `(if X)` only run when flag X is true.

**Steps 1-10 (planning — run with `--plan-only`):**
1. Pick or fetch the specified GitHub issue
2. Realign the issue with the current system (rewrite issue body, post comment)
3. Triage the issue → choose track + flags
4. Plan with nano-spec (lite or full plan depth based on triage)
5. Create a branch and draft PR
6. Write BDD test specifications (user-perspective scenarios) `(if needs_bdd)`
7. Write bug reproduction test `(if needs_repro)`
8. Generate UI designs with superdesign (auto-detected)
9. Formulate top-5 decisions interview
10. Post the Review Gate (plan + spec/repro + designs + interview)

— STOP at the Review Gate. User answers the interview, replies on PR. —

**Steps 11-20 (implementation — run with `--implement-only`):**
11. Process the interview reply (re-do BDD/repro if scope changed)
12. Implement in phases with JIT testing
13. UI fidelity check (auto-detected)
14. Automate BDD tests `(if needs_bdd)`
15. BDD guard — hard fail + auto-fix loop `(if needs_bdd)`
16. Run and fix BDD tests `(if needs_bdd)`
17. Run the full test suite (also runs the bug reproduction test if any)
18. Self-review the PR
19. Generate proof `(if needs_proof)`
20. Submit for human review

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
