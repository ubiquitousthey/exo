# Dev-Loop Agent

An autonomous development agent that drives the full lifecycle from GitHub issue to pull request. Picks up a `claude-ready` issue, plans, implements, tests, self-reviews, and submits a PR for human review.

Each step is implemented as a standalone skill or agent that can be invoked independently. This agent coordinates them in sequence, passing context between steps.

## When to Use

Invoked via the `/dev-loop` command. Requires a GitHub repository with `gh` CLI authenticated.

## Arguments

- `--repo owner/repo` — Target repository (optional, defaults to current repo)
- `--issue N` — Specific issue number to work on (optional, defaults to picking the oldest `claude-ready` issue)
- `--plan-only` — Execute only steps 1-10 (realignment, triage, planning, BDD spec / bug repro, UI design, interview formulation), then stop at the Review Gate and report the plan. Used by the command when `--review-plan` is specified.
- `--implement-only` — Execute only steps 11-20 (interview parse + implementation + tests + submit). Requires `--issue N`. Assumes steps 1-10 were already completed (branch exists, nano-spec exists, BDD feature or repro test exists per track, realignment was applied, interview was posted at the gate). Used by the command after the user approves the plan.

## Execution Modes

**Full mode (default):** Execute all 20 steps sequentially. Many steps are conditional on the triage track and its flag set — a chore may run as few as 8 steps; a feature with UI may run all 20.

**Plan-only mode (`--plan-only`):** Execute steps 1-10, then STOP at the Review Gate. Report back:
- The issue number and title
- A summary of any realignment drift detected (Step 2)
- The triage track and flags (Step 3)
- The branch name
- The nano-spec task directory path
- The BDD feature file path (if the track called for one)
- The bug reproduction test path (if the track called for one)
- UI design file paths (if Step 8 generated designs)
- The top-5 interview questions posted to the PR
- A brief summary of the planned phases from `todo.md`

Do NOT proceed to step 11. The command layer will present this to the user for review.

**Implement-only mode (`--implement-only`):** Skip steps 1-10. Read the existing nano-spec state from `tasks/<feature-slug>/` to pick up where planning left off:
1. Read `todo.md` to understand the phases
2. Read `log.md` to understand what's been done
3. Read the BDD feature file (path from the task directory) if `needs_bdd`
4. Read the reproduction test path if `needs_repro`
5. Read the triage flags (stored in nano-spec — see Step 3)
6. Check out the existing branch: `dev-loop/<issue-number>-*`
7. Execute steps 11-20

## State Management

The nano-spec task directory (`tasks/<feature-slug>/*`) IS the state. Read `todo.md` checkboxes to know which phase you're in and `log.md` to know what's been done. No separate state file is needed.

**Triage flags** are persisted as a `<!-- triage ... -->` HTML comment block at the bottom of `tasks/<feature-slug>/README.md` so resume mode can recover them:
```html
<!-- triage
track: feature | bug | refactor | chore | spike
plan_depth: full | lite
needs_bdd: true | false
needs_repro: true | false
needs_proof: true | false
-->
```

**Interview state** is persisted at `tasks/<feature-slug>/interview.md` (the question block) plus a `## Decisions` section in `doc.md` (post-parse).

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
   - `README.md` for traceability (issue number, REQ-ID, BDD feature path) AND the `<!-- triage ... -->` flag block
   - `todo.md` for phase progress
   - `log.md` for what's been done (if present — `lite` plans skip `log.md`)
   - `interview.md` for the posted top-5 decisions (if present)
2. Check out the branch:
   ```bash
   git checkout dev-loop/<issue-number>-<feature-slug>
   ```
3. Invoke the `realign` skill with action `check`. If the issue has been edited since the last realignment marker, surface the drift report and pause for the user before continuing.
4. Invoke the `review-gate` skill with action `check` to read PR feedback. The check returns the user's reply text (used in the next sub-step).
   - If feedback was left without `lgtm`/Q-answers, incorporate changes into the nano-spec and/or BDD feature file. Commit and push the updates.
   - If no approval comment is found, warn the user and ask whether to proceed.
5. Skip directly to **Step 11** (Process Interview Reply) and continue from there. Step 11 runs `interview parse` if `interview.md` exists, applies any scope changes (re-running the BDD spec authoring loop if needed), then dev-loop continues with Step 12.

If the nano-spec task directory doesn't exist, report an error and stop.

## Model Routing

Not all steps require the same level of reasoning. Dispatch each step as a sub-agent using the Agent tool's `model` parameter to balance cost and capability.

| Model | Steps | Rationale |
|-------|-------|-----------|
| **opus** | 2 (realign), 4 (nano-spec plan), 6 (BDD spec), 7 (bug repro), 8 (UI design), 9 (formulate interview), 12 (implement), 15 (BDD guard auto-fix), 18 (self-review) | Architectural decisions, drift detection, spec authoring, decision identification, complex implementation, critical analysis |
| **sonnet** | 1 (pick issue), 3 (triage), 5 (branch/PR), 10 (review-gate post), 11 (interview parse), 13 (UI fidelity), 14 (automate BDD), 15 (guard scan), 16 (BDD test loop), 17 (full test suite), 19 (proof), 20 (submit PR) | Mechanical execution, classification, parsing structured replies, running commands, following established patterns |

Note: Step 15 has two phases — the guard *scan* (sonnet) and the auto-fix *rewrite* (opus). Spawn each as a separate sub-agent.

**How to apply:** For each step, spawn a sub-agent via the Agent tool with the appropriate `model` parameter. Pass the full skill invocation instructions and all required context (issue number, feature slug, paths, REQ-ID, etc.) in the agent prompt. The sub-agent executes the step and returns its results, which you use to continue the workflow.

**Override:** If a sonnet-routed step fails twice due to reasoning limitations (not test failures or API errors), retry it with opus.

## Progress Tracking

Use `TaskCreate` to maintain a visible task list of the steps you will run. The user watches this list to see progress in real time — do NOT skip this.

**Initial list:**
- **Full or plan-only mode**: At the very start of the workflow, create a single placeholder task `"Run dev-loop workflow"` so the user sees activity immediately. Mark it `in_progress` while you run Steps 1–3. After Step 3 returns the triage flags, replace the placeholder with the full filtered list (see filter rules below).
- **Implement-only mode**: At the very start of Step 11, read the persisted triage flags from the nano-spec `README.md`, then create the filtered list directly.

**Filter rules** (drop a step from the list if it won't run):
- Full mode: include steps 1–20.
- Plan-only mode: include steps 1–10.
- Implement-only mode: include steps 11–20.
- For each conditional step, drop it if the `(if <flag>)` annotation in its header evaluates false against the triage flag set. Conditional steps: 6 (`needs_bdd`), 7 (`needs_repro`), 14/15/16 (`needs_bdd`), 19 (`needs_proof`). Steps 8 and 13 are auto-detected by their skills — keep them in the list and let the skill no-op if it decides not to run.

**Task title format**: use the step heading verbatim, e.g. `"Step 4 — Plan with nano-spec"`, `"Step 12 — Implement Phases"`.

**During execution:**
- Mark a task `in_progress` immediately before dispatching its sub-agent.
- Mark it `completed` when the sub-agent returns successfully.
- If a step pauses for the user (low triage confidence, realignment drift, BDD guard exhausted, etc.), leave the task `in_progress` while you surface the pause — the in-progress marker tells the user where the loop stalled.
- If a step fails and you retry, keep the task `in_progress` across the retry attempts.

## Workflow

Execute the following 20 steps sequentially. Many are conditional on the triage track and flag set produced in Step 3 — skip cleanly when the flag is `false`. After each non-trivial step, update the nano-spec `log.md` with what was done (skip `log.md` when `plan_depth=lite`). If `--resume` was provided, skip to Step 11.

**Dispatch each step as a sub-agent using the model specified in the Model Routing table above.**

**When `--plan-only` is set, execute ONLY steps 1-10, then stop.**
**When `--implement-only` is set, skip steps 1-10, execute steps 11-20.**

**Track progress with `TaskCreate`** — see the Progress Tracking section above. Create the task list before/alongside Step 1 (or Step 11 in implement-only mode) and update it as each step starts and completes.

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
4. Update the locally-stored issue body used by all subsequent steps with the new realigned body.

---

### Step 3 — Triage

Invoke the `triage` skill with action `classify`.

Pass: issue number, issue title, realigned issue body.

1. The skill returns `track`, `confidence`, and a flag set: `plan_depth`, `needs_bdd`, `needs_repro`, `needs_proof`.
2. **If `confidence=low`** → Pause and confirm the track with the user before continuing. Mismatching the track wastes more time later than asking now.
3. Persist the flags as a `<!-- triage ... -->` block at the bottom of the nano-spec `README.md` once it exists (the persistence happens at the end of Step 4 since the nano-spec dir doesn't exist yet). Hold the flags in memory until then.
4. Use the flags to gate downstream steps. **Throughout the rest of the workflow, "(if `<flag>`)" annotations on a step header mean: skip the step entirely if the flag is false.**

---

### Step 4 — Plan with nano-spec

Invoke the `nano-spec` skill with action `create`. Pass `$PLAN_DEPTH` from the triage flag.

1. Invoke `nano-spec create <feature-slug> "<issue title>: <realigned issue body summary>" $PLAN_DEPTH`.
   - On `lite` plans the small template is used: minimal `README.md`, minimal `todo.md`, no `doc.md`, no `log.md`.
   - On `full` plans the medium/large template is used per nano-spec's complexity rules.
2. **Populate the Traceability section** in the generated `README.md`:
   - **Source**: `#<issue-number>` (and `REQ-XXX` if available)
   - **BDD Feature**: *(to be populated after Step 6 if `needs_bdd`)*
   - **Reproduction Test**: *(to be populated after Step 7 if `needs_repro`)*
3. **Append the triage `<!-- triage ... -->` block** to the bottom of `README.md` so resume mode can recover the flags.
4. Review and refine `todo.md`: break large tasks into phases, add research items. Verify ACs follow the user-perspective rule (actor + observable outcome) — rewrite or move to `doc.md` (or simply drop on `lite` plans where there is no `doc.md`).
5. If `plan_depth=full`, review `doc.md` and populate Open Questions.
6. **If there are unresolvable open questions blocking the plan structure** → Pause and ask the user. Otherwise, all other open questions roll into Step 9 (interview formulation) for the gate.

---

### Step 5 — Create Branch & Draft PR

Invoke the `branch-pr` skill with action `create`.

Pass: issue number, feature slug, issue title, repo (if provided), REQ-ID (if available), nano-spec path.

Store the returned PR number and URL for subsequent steps.

---

### Step 6 — Write BDD Test Spec (if `needs_bdd`)

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

If `needs_bdd=false`, skip this step.

---

### Step 7 — Write Bug Reproduction Test (if `needs_repro`)

Invoke the `bug-repro` skill with action `write`.

Pass: issue number, issue title, realigned issue body, REQ-ID (if available).

1. The skill detects the test framework, parses the bug report's "Steps to reproduce" and "Expected behavior", writes a single regression test asserting the FIXED behavior, runs it once against current main (it should fail), and commits.
2. **If the skill aborts with "no reproducible steps"** → Pause and ask the user for clearer reproduction steps, or downgrade the track from `bug` to `spike`.
3. **If the skill reports the bug is already fixed** (test passes on main) → Pause. The issue may be stale; ask the user before continuing.
4. Store the test file path.
5. **Update the nano-spec** `README.md` Traceability section with the reproduction test path.

If `needs_repro=false`, skip this step.

---

### Step 8 — UI Design (auto-detected)

Invoke the `ui-design` skill with action `generate`.

Pass: issue title, issue body, BDD feature path (if any), nano-spec path, issue number, REQ-ID (if available).

The skill auto-detects whether the work is UI work and no-ops if not. No triage flag governs this — the skill's own detection is authoritative.

---

### Step 9 — Formulate Interview

Invoke the `interview` skill with action `formulate`.

Pass: nano-spec path.

1. The skill scores candidate decisions (open questions in the issue body, open questions in `doc.md` if present, recorded decisions in `doc.md`, and implicit assumptions identified in the plan), picks the top 5, and writes the question block to `tasks/<feature-slug>/interview.md`.
2. Capture the question block as a string for the next step.
3. **If the skill returns "no decisions above threshold"** → No interview is needed. Pass an empty interview block to Step 10.

---

### Step 10 — Review Gate

Invoke the `review-gate` skill with action `post`.

Pass: PR number, nano-spec path, BDD feature path (if `needs_bdd`), reproduction test path (if `needs_repro`), feature slug, design paths (if Step 8 generated designs), interview block (from Step 9, may be empty), track (from Step 3), repo (if provided).

The skill posts a single comment containing the plan, the spec/repro test for this track, the UI designs (if any), and the interview questions (if any). It adds the `dev-loop-review-gate` label.

**Stop execution.** The user will review on GitHub, optionally answer the interview questions, and resume with `/dev-loop --resume <feature-slug>`.

**If `--plan-only` is set, STOP HERE.** Report the issue, realignment summary, triage track and flags, branch, nano-spec directory, BDD feature path or reproduction test path, UI designs (if any), interview questions, and phase summary.

---

### Step 11 — Process Interview Reply

Resume entry point. Run only when picking up from the Review Gate (after `--resume` or when continuing past Step 10).

1. Use the interview reply text returned by `review-gate check` (collected during the resume flow).
2. **If `tasks/<feature-slug>/interview.md` exists**, invoke `interview parse`. Pass: nano-spec path, issue number, the reply text, repo.
3. The skill writes answers into `doc.md` `## Decisions` and computes `scope_changed`.
4. **If `scope_changed=true` AND `needs_bdd=true`**: re-run Step 6 (BDD spec authoring) so the scenarios reflect the answered decisions, then re-run Step 14 → Step 15 → Step 16 (BDD automation + guard + test loop) after implementation lands. The simplest pattern: just re-run Step 6 now and let the rest of the pipeline catch up.
5. **If `scope_changed=true` AND `needs_repro=true`**: re-run Step 7 to update the reproduction test in light of the answered decisions.
6. **If `scope_changed=false` or no interview existed**: continue to Step 12.

---

### Step 12 — Implement Phases

Invoke the `implement-phases` skill with action `run` (or `resume` if picking up from a partial run).

Pass: nano-spec path, issue number, REQ-ID (if available), design paths (if Step 8 generated designs).

**If `--implement-only` is set, start at Step 11, then proceed here.** First recover state by reading the nano-spec task directory and checking out the branch.

---

### Step 13 — UI Fidelity Check (auto-detected)

Invoke the `ui-verify` skill with action `check`.

Pass: nano-spec path, base branch (`main` or as appropriate), issue number, REQ-ID (if available).

The skill handles skip detection, static audit, visual comparison, fix loops, and artifact archiving.

---

### Step 14 — Automate BDD Tests (if `needs_bdd`)

Invoke the `bdd-author` skill with action `automate`.

1. Pass the feature file path from Step 6.
2. Fill in step definition bodies with real entry points and observable assertions per the Step Definition Rules in the `bdd-author` skill. No `TODO`-and-`pass` bodies — write real bodies even if the implementation isn't ready (the test can fail until it lands).
3. Commit and push the step definitions.

If `needs_bdd=false`, skip this step.

---

### Step 15 — BDD Guard (if `needs_bdd`)

Invoke the `bdd-author` skill with action `guard`. Pass: paths to the step definition files written in Step 14, the feature file path, and the issue number.

**Hard fail with auto-fix loop.** Behavior:

1. Run the guard scan (sonnet sub-agent). If `BDD Guard: PASS`, proceed to Step 16.
2. If `FAIL`, dispatch an opus sub-agent to rewrite each offending step body per the findings — drive a real entry point and assert observable outputs as defined in the `bdd-author automate` Step Definition Rules.
3. Re-run the guard. Repeat the rewrite/scan cycle up to **3 iterations**.
4. If still failing after 3 iterations, **pause and ask the user**. Persistent anti-patterns usually mean the AC isn't actually user-observable and needs to be reworked upstream (Step 4 nano-spec → Step 6 feature file).
5. After PASS, commit and push the rewritten step definitions:
   ```bash
   git add <step-defs-files>
   git commit -m "test: align BDD step definitions with user-perspective rule for #<number>"
   ```

If `needs_bdd=false`, skip this step.

---

### Step 16 — BDD Fix/Test Loop (if `needs_bdd`)

Invoke the `test-loop` skill with action `bdd`.

Pass: feature file path, issue number.

The skill handles test execution, failure analysis, fix iterations (max 5), and user escalation.

If `needs_bdd=false`, skip this step.

---

### Step 17 — Full Test Suite

Invoke the `test-loop` skill with action `full`.

Pass: issue number.

The skill handles runner detection, execution, regression analysis, fix iterations (max 3), and committing fixes. On the bug track, this is also where the reproduction test from Step 7 must turn green; if it doesn't, the fix is incomplete.

---

### Step 18 — Self-Review

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
6. Store the self-review summary for Step 20.

---

### Step 19 — Generate Proof (if `needs_proof`)

Invoke the `showboat-proof` skill with action `prove`.

Pass: the issue title and body as feature context, the BDD feature file path (if any), the REQ-ID and issue number for traceability.

1. Review the generated proof document for quality.
2. Commit and push:
   ```bash
   git add proofs/<feature-slug>/
   git commit -m "docs: add showboat proof for #<number> [REQ-XXX]"
   ```
   Include `[REQ-XXX]` only if a REQ-ID is available.

If `needs_proof=false`, skip this step.

---

### Step 20 — Submit for Review

Invoke the `submit-pr` skill with action `submit`.

Pass: PR number, issue number, feature slug, nano-spec path, BDD feature path (if any), reproduction test path (if any), proof path (if any), self-review summary, BDD result (if BDD ran), test suite result, fidelity rating and report path (if Step 13 ran), track (from Step 3), REQ-ID (if available), phase directory (if known), repo (if provided).

Report the final status to the user with a link to the PR.
