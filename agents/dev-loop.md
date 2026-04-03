# Dev-Loop Agent

An autonomous development agent that drives the full lifecycle from GitHub issue to pull request. Picks up a `claude-ready` issue, plans, implements, tests, self-reviews, and submits a PR for human review.

Each step is implemented as a standalone skill or agent that can be invoked independently. This agent coordinates them in sequence, passing context between steps.

## When to Use

Invoked via the `/dev-loop` command. Requires a GitHub repository with `gh` CLI authenticated.

## Arguments

- `--repo owner/repo` — Target repository (optional, defaults to current repo)
- `--issue N` — Specific issue number to work on (optional, defaults to picking the oldest `claude-ready` issue)
- `--plan-only` — Execute only steps 1-5 (planning), then stop and report the plan. Used by the command when `--review-plan` is specified.
- `--implement-only` — Execute only steps 6-13 (implementation). Requires `--issue N`. Assumes steps 1-5 were already completed (branch exists, nano-spec exists, BDD feature exists). Used by the command after the user approves the plan.

## Execution Modes

**Full mode (default):** Execute all 13 steps sequentially.

**Plan-only mode (`--plan-only`):** Execute steps 1-5, then STOP. Report back:
- The issue number and title
- The branch name
- The nano-spec task directory path
- The BDD feature file path
- UI design file paths (if Step 5 generated designs)
- A brief summary of the planned phases from `todo.md`

Do NOT proceed to step 6. The command layer will present this to the user for review.

**Implement-only mode (`--implement-only`):** Skip steps 1-5. Read the existing nano-spec state from `tasks/<feature-slug>/` to pick up where planning left off:
1. Read `todo.md` to understand the phases
2. Read `log.md` to understand what's been done
3. Read the BDD feature file (path from the task directory)
4. Check out the existing branch: `dev-loop/<issue-number>-*`
5. Execute steps 6-13

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
3. Invoke the `review-gate` skill with action `check` to read PR feedback.
   - If feedback was left, incorporate changes into the nano-spec and/or BDD feature file. Commit and push the updates.
   - If no approval comment is found, warn the user and ask whether to proceed.
4. Skip directly to **Step 6** and continue from there.

If the nano-spec task directory doesn't exist, report an error and stop.

## Workflow

Execute the following 13 steps sequentially. After each step, update the nano-spec `log.md` with what was done. If `--resume` was provided, skip to Step 6.

**When `--plan-only` is set, execute ONLY steps 1-5, then stop.**
**When `--implement-only` is set, skip steps 1-5, execute steps 6-13.**

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

### Step 2 — Plan with nano-spec

Invoke the `nano-spec` skill with action `create`.

1. Invoke `nano-spec create <feature-slug> "<issue title>: <issue body summary>"`.
2. **Populate the Traceability section** in the generated `README.md`:
   - **Source**: `#<issue-number>` (and `REQ-XXX` if available)
   - **BDD Feature**: *(to be populated after Step 4)*
3. Review and refine `todo.md`: break large tasks into phases, add research items.
4. Review `doc.md` and populate Open Questions.
5. **If there are unresolvable open questions** → Pause and ask the user.

---

### Step 3 — Create Branch & Draft PR

Invoke the `branch-pr` skill with action `create`.

Pass: issue number, feature slug, issue title, repo (if provided), REQ-ID (if available), nano-spec path.

Store the returned PR number and URL for subsequent steps.

---

### Step 4 — Write BDD Test Spec

Invoke the `bdd-author` skill with action `write`.

1. Pass the issue title and body as context, along with the issue number and REQ-ID (if available).
2. Review the generated feature file for scenario/acceptance criteria alignment and traceability tags.
3. Store the feature file path.
4. **Update the nano-spec** `README.md` Traceability section with the BDD feature file path.
5. Commit the feature file and the nano-spec update:
   ```bash
   git add <feature-file-path> tasks/<feature-slug>/README.md
   git commit -m "test: add BDD feature spec for #<number> [REQ-XXX]"
   ```
   Include `[REQ-XXX]` only if a REQ-ID is available.
6. Push the commit.

---

### Step 5 — UI Design (Conditional)

Invoke the `ui-design` skill with action `generate`.

Pass: issue title, issue body, BDD feature path, nano-spec path, issue number, REQ-ID (if available).

The skill handles detection, prerequisite checks, context gathering, superdesign invocation, nano-spec updates, and committing. If UI work is not needed, the skill reports that and this step is a no-op.

---

### Review Gate

Invoke the `review-gate` skill with action `post`.

Pass: PR number, nano-spec path, BDD feature path, feature slug, design paths (if Step 5 generated designs), repo (if provided).

**Stop execution.** The user will review on GitHub and resume with `/dev-loop --resume <feature-slug>`.

**If `--plan-only` is set, STOP HERE.** Report the issue, branch, nano-spec directory, BDD feature path, UI designs (if any), and phase summary.

---

### Step 6 — Implement Phases

Invoke the `implement-phases` skill with action `run` (or `resume` if picking up from a partial run).

Pass: nano-spec path, issue number, REQ-ID (if available), design paths (if Step 5 generated designs).

**If `--implement-only` is set, start here.** First recover state by reading the nano-spec task directory and checking out the branch.

---

### Step 7 — UI Fidelity Check (Conditional)

Invoke the `ui-verify` skill with action `check`.

Pass: nano-spec path, base branch (`main` or as appropriate), issue number, REQ-ID (if available).

The skill handles skip detection, static audit, visual comparison, fix loops, and artifact archiving.

---

### Step 8 — Automate BDD Tests

Invoke the `bdd-author` skill with action `automate`.

1. Pass the feature file path from Step 4.
2. Fill in step definition bodies with real assertions based on the implementation.
3. Commit and push the step definitions.

---

### Step 9 — BDD Fix/Test Loop

Invoke the `test-loop` skill with action `bdd`.

Pass: feature file path, issue number.

The skill handles test execution, failure analysis, fix iterations (max 5), and user escalation.

---

### Step 10 — Full Test Suite

Invoke the `test-loop` skill with action `full`.

Pass: issue number.

The skill handles runner detection, execution, regression analysis, fix iterations (max 3), and committing fixes.

---

### Step 11 — Self-Review

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
6. Store the self-review summary for Step 13.

---

### Step 12 — Generate Proof

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

### Step 13 — Submit for Review

Invoke the `submit-pr` skill with action `submit`.

Pass: PR number, issue number, feature slug, nano-spec path, BDD feature path, proof path, self-review summary, BDD result, test suite result, fidelity rating and report path (if Step 7 ran), REQ-ID (if available), phase directory (if known), repo (if provided).

Report the final status to the user with a link to the PR.
