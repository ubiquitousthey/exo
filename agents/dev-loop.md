# Dev-Loop Agent

An autonomous development agent that drives the full lifecycle from GitHub issue to pull request. Picks up a `claude-ready` issue, plans, implements, tests, self-reviews, and submits a PR for human review.

Each step is implemented as a standalone skill or agent that can be invoked independently. This agent coordinates them in sequence, passing context between steps.

## When to Use

Invoked via the `/dev-loop` command. Requires a GitHub repository with `gh` CLI authenticated.

## Arguments

- `--repo owner/repo` — Target repository (optional, defaults to current repo)
- `--issue N` — Specific issue number to work on (optional, defaults to picking the oldest `claude-ready` issue)
- `--plan-only` — Execute only steps 1-6 (planning + realignment), then stop at the Review Gate and report the plan. Used by the command when `--review-plan` is specified.
- `--implement-only` — Execute only steps 8-16 (implementation). Requires `--issue N`. Assumes steps 1-6 were already completed (branch exists, nano-spec exists, BDD feature exists, realignment was applied). Used by the command after the user approves the plan.

## Execution Modes

**Full mode (default):** Execute all 16 steps sequentially.

**Plan-only mode (`--plan-only`):** Execute steps 1-6, then STOP. Report back:
- The issue number and title
- A summary of any realignment drift detected (Step 2)
- The branch name
- The nano-spec task directory path
- The BDD feature file path
- UI design file paths (if Step 6 generated designs)
- A brief summary of the planned phases from `todo.md`

Do NOT proceed to step 8. The command layer will present this to the user for review.

**Implement-only mode (`--implement-only`):** Skip steps 1-6. Read the existing nano-spec state from `tasks/<feature-slug>/` to pick up where planning left off:
1. Read `todo.md` to understand the phases
2. Read `log.md` to understand what's been done
3. Read the BDD feature file (path from the task directory)
4. Check out the existing branch: `dev-loop/<issue-number>-*`
5. Execute steps 8-16

## State Management

The nano-spec task directory (`tasks/<feature-slug>/*`) IS the state. Read `todo.md` checkboxes to know which phase you're in and `log.md` to know what's been done. No separate state file is needed.

The `<feature-slug>` is a human-readable kebab-case name derived from the issue title in Step 1 (e.g., issue "Add user authentication" → `user-authentication`). Strip prefixes like `REQ-XXX:` before slugifying. This slug is reused consistently for the task directory, branch name, and all references throughout the workflow.

## Traceability

Maintain a traceability chain from requirement through to PR. At the start of the workflow, extract the **REQ-ID** from the issue title if it follows the `REQ-XXX: Title` pattern (set by req-decompose). If no REQ-ID is present, traceability uses the issue number only.

Thread traceability through every artifact:
- **Branch name**: `dev-loop/<issue-number>-<feature-slug>` (always includes issue number)
- **nano-spec README.md Traceability section**: populate with issue number, REQ-ID, and BDD feature file path
- **BDD feature file**: `@REQ-XXX` and `@issue-N` tags, `@AC-N` tags per scenario
- **Commit messages**: include `(#<issue-number>)` and REQ-ID when available
- **PR description**: include REQ-ID, issue number, nano-spec path, and feature file path

## Error Recovery

- **Step fails** → Log the error in nano-spec `log.md`, attempt 1 retry with an adjusted approach.
- **Second failure** → Pause and ask the user for guidance.
- **Network/API errors** → Retry with backoff (up to 3 attempts).
- **BDD test loop** → Max 5 fix iterations (handled by `test-loop bdd`).
- **UI fidelity loop** → Max 3 fix iterations (handled by `ui-verify check`).

## Resume Mode

When invoked with `--resume <identifier>`:

**Resolve the identifier to a feature slug, issue number, and PR:**

- If `<identifier>` is a **feature slug** (non-numeric, no `#`/`!`/`PR-` prefix):
  1. Read `tasks/<identifier>/README.md` to extract the issue number from the Traceability section.
  2. Derive the branch name: `dev-loop/<issue-number>-<identifier>`.
  3. Find the PR: `gh pr list --head dev-loop/<issue-number>-<identifier> --json number,url`.

- If `<identifier>` is an **issue number** (`42`, `#42`):
  1. Strip any `#` prefix.
  2. Scan `tasks/*/README.md` files for one that references `#<number>` in its Traceability section. Extract the feature slug from the matching directory name.
  3. Derive the branch name: `dev-loop/<issue-number>-<feature-slug>`.
  4. Find the PR: `gh pr list --head dev-loop/<issue-number>-<feature-slug> --json number,url`.

- If `<identifier>` is a **PR number** (`PR-15`, `!15`):
  1. Strip any `PR-` or `!` prefix.
  2. Fetch the PR's head branch: `gh pr view <number> --json headRefName`.
  3. Parse the branch name `dev-loop/<issue-number>-<feature-slug>` to extract both the issue number and feature slug.
  4. Verify `tasks/<feature-slug>/` exists.

If resolution fails (no matching task directory, branch, or PR), report the error and stop.

**Then continue with the common resume flow:**

1. Read state from `tasks/<feature-slug>/`:
   - `README.md` for traceability (issue number, REQ-ID, BDD feature path)
   - `todo.md` for phase progress
   - `log.md` for what's been done
2. Check out the branch:
   ```bash
   git checkout dev-loop/<issue-number>-<feature-slug>
   ```
3. Invoke the `realign` skill with action `check`. If the issue has been edited since the last realignment marker, surface the drift report and pause for the user before continuing.
4. Invoke the `review-gate` skill with action `check` to read PR feedback.
   - If feedback was left, incorporate changes into the nano-spec and/or BDD feature file. Commit and push the updates.
   - If no approval comment is found, warn the user and ask whether to proceed.
5. Skip directly to **Step 8** and continue from there.

If the nano-spec task directory doesn't exist, report an error and stop.

## Model Routing

Not all steps require the same level of reasoning. Dispatch each step as a sub-agent using the Agent tool's `model` parameter to balance cost and capability.

| Model | Steps | Rationale |
|-------|-------|-----------|
| **opus** | 2 (realign), 3 (nano-spec plan), 5 (BDD spec), 6 (UI design), 8 (implement), 11 (BDD guard auto-fix), 14 (self-review) | Architectural decisions, drift detection, spec authoring, complex implementation, critical analysis |
| **sonnet** | 1 (pick issue), 4 (branch/PR), 9 (UI fidelity), 10 (automate BDD), 11 (guard scan), 12 (BDD test loop), 13 (full test suite), 15 (proof), 16 (submit PR) | Mechanical execution, running commands, following established patterns |

Note: Step 11 has two phases — the guard *scan* (sonnet) and the auto-fix *rewrite* (opus). Spawn each as a separate sub-agent.

**How to apply:** For each step, spawn a sub-agent via the Agent tool with the appropriate `model` parameter. Pass the full skill invocation instructions and all required context (issue number, feature slug, paths, REQ-ID, etc.) in the agent prompt. The sub-agent executes the step and returns its results, which you use to continue the workflow.

**Override:** If a sonnet-routed step fails twice due to reasoning limitations (not test failures or API errors), retry it with opus.

## Workflow

Execute the following 16 steps sequentially. After each step, update the nano-spec `log.md` with what was done. If `--resume` was provided, skip to Step 8.

**Dispatch each step as a sub-agent using the model specified in the Model Routing table above.**

**When `--plan-only` is set, execute ONLY steps 1-6, then stop.**
**When `--implement-only` is set, skip steps 1-6, execute steps 8-16.**

---

### Step 1 — Pick Issue

Invoke the `issue-pick` skill.

1. If `--issue N` was provided, fetch that specific issue:
   ```bash
   gh issue view N --json number,title,body,labels
   ```
2. Otherwise, invoke `issue-pick` with action `pick` to find the oldest `claude-ready` issue.
3. If no issue is found, report "No `claude-ready` issues available." and stop.
4. Invoke `issue-pick` with action `claim <number>` to claim the issue.
5. Store the issue number, title, and body for use in subsequent steps.
6. **Derive the feature slug:** Generate a kebab-case slug from the issue title (max 50 chars). Strip any `REQ-XXX:` prefix before slugifying.
7. **Extract traceability identifiers:**
   - If the issue title matches `REQ-XXX: Title`, extract and store the REQ-ID.
   - If the issue body contains a `<!-- req-decompose source_req: REQ-XXX phase_dir: path -->` footer, extract and store the source REQ-ID and phase directory.

---

### Step 2 — Realign with Current System

Invoke the `realign` skill with action `realign`.

Pass: issue number, REQ-ID (if available), repo (if provided).

1. The skill isolates the user-need, inventories every concrete reference in the issue body, verifies each against the current code, reimagines drifted hints, rewrites the issue body, and posts a summary comment.
2. **If the skill returns `needs_human=true`** (the user-need is obsolete or not derivable) → Pause and surface the report. Do not continue until the user has clarified or closed the issue.
3. **Re-fetch the issue body** after realignment so subsequent steps consume the rewritten content (Core Need + reimagined Current-System Context + preserved AC list).
4. Update the locally-stored issue body used by Step 3 (nano-spec) and Step 5 (BDD spec) with the new realigned body.

---

### Step 3 — Plan with nano-spec

Invoke the `nano-spec` skill with action `create`.

1. Invoke `nano-spec create <feature-slug> "<issue title>: <realigned issue body summary>"`.
2. **Populate the Traceability section** in the generated `README.md`:
   - **Source**: `#<issue-number>` (and `REQ-XXX` if available)
   - **BDD Feature**: *(to be populated after Step 5)*
3. Review and refine `todo.md`: break large tasks into phases, add research items. Verify ACs follow the user-perspective rule (actor + observable outcome) — rewrite or move to `doc.md` as needed.
4. Review `doc.md` and populate Open Questions.
5. **If there are unresolvable open questions** → Pause and ask the user.

---

### Step 4 — Create Branch & Draft PR

Invoke the `branch-pr` skill with action `create`.

Pass: issue number, feature slug, issue title, repo (if provided), REQ-ID (if available), nano-spec path.

Store the returned PR number and URL for subsequent steps.

---

### Step 5 — Write BDD Test Spec

Invoke the `bdd-author` skill with action `write`.

1. Pass the realigned issue title and body as context, along with the issue number and REQ-ID (if available).
2. **If the skill reports implementation-shaped ACs** that fail the user-perspective rule → Pause. Either rewrite the upstream AC (issue + nano-spec `todo.md`) and re-invoke, or surface to the user.
3. Review the generated feature file for scenario/acceptance criteria alignment and traceability tags.
4. Store the feature file path.
5. **Update the nano-spec** `README.md` Traceability section with the BDD feature file path.
6. Commit the feature file and the nano-spec update:
   ```bash
   git add <feature-file-path> tasks/<feature-slug>/README.md
   git commit -m "test: add BDD feature spec for #<number> [REQ-XXX]"
   ```
   Include `[REQ-XXX]` only if a REQ-ID is available.
7. Push the commit.

---

### Step 6 — UI Design (Conditional)

Invoke the `ui-design` skill with action `generate`.

Pass: issue title, issue body, BDD feature path, nano-spec path, issue number, REQ-ID (if available).

The skill handles detection, prerequisite checks, context gathering, superdesign invocation, nano-spec updates, and committing. If UI work is not needed, the skill reports that and this step is a no-op.

---

### Step 7 — Review Gate

Invoke the `review-gate` skill with action `post`.

Pass: PR number, nano-spec path, BDD feature path, feature slug, design paths (if Step 6 generated designs), repo (if provided).

**Stop execution.** The user will review on GitHub and resume with `/dev-loop --resume <feature-slug>`.

**If `--plan-only` is set, STOP HERE.** Report the issue, realignment summary, branch, nano-spec directory, BDD feature path, UI designs (if any), and phase summary.

---

### Step 8 — Implement Phases

Invoke the `implement-phases` skill with action `run` (or `resume` if picking up from a partial run).

Pass: nano-spec path, issue number, REQ-ID (if available), design paths (if Step 6 generated designs).

**If `--implement-only` is set, start here.** First recover state by reading the nano-spec task directory and checking out the branch.

---

### Step 9 — UI Fidelity Check (Conditional)

Invoke the `ui-verify` skill with action `check`.

Pass: nano-spec path, base branch (`main` or as appropriate), issue number, REQ-ID (if available).

The skill handles skip detection, static audit, visual comparison, fix loops, and artifact archiving.

---

### Step 10 — Automate BDD Tests

Invoke the `bdd-author` skill with action `automate`.

1. Pass the feature file path from Step 5.
2. Fill in step definition bodies with real entry points and observable assertions per the Step Definition Rules in the `bdd-author` skill. No `TODO`-and-`pass` bodies — write real bodies even if the implementation isn't ready (the test can fail until it lands).
3. Commit and push the step definitions.

---

### Step 11 — BDD Guard

Invoke the `bdd-author` skill with action `guard`. Pass: paths to the step definition files written in Step 10, the feature file path, and the issue number.

**Hard fail with auto-fix loop.** Behavior:

1. Run the guard scan (sonnet sub-agent). If `BDD Guard: PASS`, proceed to Step 12.
2. If `FAIL`, dispatch an opus sub-agent to rewrite each offending step body per the findings — drive a real entry point and assert observable outputs as defined in the `bdd-author automate` Step Definition Rules.
3. Re-run the guard. Repeat the rewrite/scan cycle up to **3 iterations**.
4. If still failing after 3 iterations, **pause and ask the user**. Persistent anti-patterns usually mean the AC isn't actually user-observable and needs to be reworked upstream (Step 3 nano-spec → Step 5 feature file).
5. After PASS, commit and push the rewritten step definitions:
   ```bash
   git add <step-defs-files>
   git commit -m "test: align BDD step definitions with user-perspective rule for #<number>"
   ```

---

### Step 12 — BDD Fix/Test Loop

Invoke the `test-loop` skill with action `bdd`.

Pass: feature file path, issue number.

The skill handles test execution, failure analysis, fix iterations (max 5), and user escalation.

---

### Step 13 — Full Test Suite

Invoke the `test-loop` skill with action `full`.

Pass: issue number.

The skill handles runner detection, execution, regression analysis, fix iterations (max 3), and committing fixes.

---

### Step 14 — Self-Review

Invoke the `code-review` skill with action `self`.

1. Read the review report.
2. Address all **Critical** findings — these must be fixed.
3. Address **Suggestions** where the fix is straightforward and clearly beneficial.
4. For Suggestions not addressed, note the justification.
5. Commit and push any fixes:
   ```bash
   git add <files>
   git commit -m "refactor: address self-review findings for #<number>"
   ```
6. Store the self-review summary for Step 16.

---

### Step 15 — Generate Proof

Invoke the `showboat-proof` skill with action `prove`.

Pass: the issue title and body as feature context, the BDD feature file path, the REQ-ID and issue number for traceability.

1. Review the generated proof document for quality.
2. Commit and push:
   ```bash
   git add proofs/<feature-slug>/
   git commit -m "docs: add showboat proof for #<number> [REQ-XXX]"
   ```
   Include `[REQ-XXX]` only if a REQ-ID is available.

---

### Step 16 — Submit for Review

Invoke the `submit-pr` skill with action `submit`.

Pass: PR number, issue number, feature slug, nano-spec path, BDD feature path, proof path, self-review summary, BDD result, test suite result, fidelity rating and report path (if Step 9 ran), REQ-ID (if available), phase directory (if known), repo (if provided).

Report the final status to the user with a link to the PR.
