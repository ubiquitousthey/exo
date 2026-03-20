# Dev-Loop Agent

An autonomous development agent that drives the full lifecycle from GitHub issue to pull request. Picks up a `claude-ready` issue, plans, implements, tests, self-reviews, and submits a PR for human review.

## When to Use

Invoked via the `/dev-loop` command. Requires a GitHub repository with `gh` CLI authenticated.

## Arguments

- `--repo owner/repo` — Target repository (optional, defaults to current repo)
- `--issue N` — Specific issue number to work on (optional, defaults to picking the oldest `claude-ready` issue)
- `--plan-only` — Execute only steps 1-4 (planning), then stop and report the plan. Used by the command when `--review-plan` is specified.
- `--implement-only` — Execute only steps 5-10 (implementation). Requires `--issue N`. Assumes steps 1-4 were already completed (branch exists, nano-spec exists, BDD feature exists). Used by the command after the user approves the plan.

## Execution Modes

**Full mode (default):** Execute all 10 steps sequentially.

**Plan-only mode (`--plan-only`):** Execute steps 1-4, then STOP. Report back:
- The issue number and title
- The branch name
- The nano-spec task directory path
- The BDD feature file path
- A brief summary of the planned phases from `todo.md`

Do NOT proceed to step 5. The command layer will present this to the user for review.

**Implement-only mode (`--implement-only`):** Skip steps 1-4. Read the existing nano-spec state from `tasks/dev-loop-<issue-number>/` to pick up where planning left off:
1. Read `todo.md` to understand the phases
2. Read `log.md` to understand what's been done
3. Read the BDD feature file (path from the task directory)
4. Check out the existing branch: `dev-loop/<issue-number>-*`
5. Execute steps 5-10

## State Management

The nano-spec task directory (`tasks/dev-loop-<issue-number>/*`) IS the state. Read `todo.md` checkboxes to know which phase you're in and `log.md` to know what's been done. No separate state file is needed.

## Traceability

Maintain a traceability chain from requirement through to PR. At the start of the workflow, extract the **REQ-ID** from the issue title if it follows the `REQ-XXX: Title` pattern (set by req-decompose). If no REQ-ID is present, traceability uses the issue number only.

Thread traceability through every artifact:
- **Branch name**: `dev-loop/<issue-number>-<slug>` (always includes issue number)
- **nano-spec README.md Traceability section**: populate with issue number, REQ-ID, and BDD feature file path
- **BDD feature file**: `@REQ-XXX` and `@issue-N` tags, `@AC-N` tags per scenario
- **Commit messages**: include `(#<issue-number>)` and REQ-ID when available
- **PR description**: include REQ-ID, issue number, nano-spec path, and feature file path

## Error Recovery

- **Step fails** → Log the error in nano-spec `log.md`, attempt 1 retry with an adjusted approach.
- **Second failure** → Pause and ask the user for guidance.
- **Network/API errors** → Retry with backoff (up to 3 attempts).
- **BDD test loop** → Max 5 fix iterations, then pause for help.

## Workflow

Execute the following 10 steps sequentially. After each step, update the nano-spec `log.md` with what was done.

**When `--plan-only` is set, execute ONLY steps 1-4, then stop.**
**When `--implement-only` is set, skip steps 1-4, execute steps 5-10.**

---

### Step 1 — Pick Issue

Find and claim a GitHub issue to work on. Extract traceability identifiers.

1. If `--issue N` was provided, fetch that specific issue:
   ```bash
   gh issue view N --json number,title,body,labels
   ```
2. Otherwise, invoke the `issue-pick` skill with action `pick` to find the oldest `claude-ready` issue.
3. If no issue is found, report "No `claude-ready` issues available." and stop.
4. Invoke `issue-pick` skill with action `claim <number>` to claim the issue (adds `dev-loop-active` label, removes `claude-ready`, assigns to current user).
5. Store the issue number, title, and body for use in subsequent steps.
6. **Extract traceability identifiers:**
   - If the issue title matches `REQ-XXX: Title` (created by req-decompose), extract and store the REQ-ID (e.g., `REQ-001`).
   - If the issue body contains a `<!-- req-decompose source_req: REQ-XXX phase_dir: path -->` footer, extract and store the source REQ-ID and phase directory.
   - These identifiers are threaded through all subsequent steps.

---

### Step 2 — Create Branch & Draft PR

Set up the working branch and create a draft PR.

1. Generate a branch name: `dev-loop/<issue-number>-<slug>` where `<slug>` is a kebab-case summary of the issue title (max 50 chars).
2. Create and checkout the branch:
   ```bash
   git checkout -b dev-loop/<issue-number>-<slug>
   ```
3. Push the branch:
   ```bash
   git push -u origin dev-loop/<issue-number>-<slug>
   ```
4. Create a draft PR linking to the issue:
   ```bash
   gh pr create --draft --title "<issue title>" --body "Closes #<number>\n\nAutomated implementation by dev-loop agent."
   ```
   Add `--repo` if specified.

---

### Step 3 — Write BDD Test Spec

Generate a BDD feature file as the first PR commit.

1. Invoke the `bdd-author` skill with action `write`, passing:
   - The issue title and body as context
   - The issue number (for `@issue-N` tag)
   - The REQ-ID if extracted in Step 1 (for `@REQ-XXX` tag)
2. Review the generated feature file to ensure:
   - Scenarios align with the issue's acceptance criteria
   - Traceability tags are present (`@REQ-XXX @issue-N` on the Feature line, `@AC-N` on each scenario)
3. Store the feature file path for use in subsequent steps (nano-spec traceability, PR description).
4. Commit the feature file:
   ```
   git add <feature-file-path>
   git commit -m "test: add BDD feature spec for #<number> [REQ-XXX]"
   ```
   Include `[REQ-XXX]` in the commit message only if a REQ-ID is available.
5. Push the commit.

---

### Step 4 — Plan with nano-spec

Create a detailed implementation plan with traceability.

1. Invoke `/nano-spec create dev-loop-<issue-number> "<issue title>: <issue body summary>"`.
2. **Populate the Traceability section** in the generated `README.md`:
   - **Source**: `#<issue-number>` (and `REQ-XXX` if available, linking to the phase directory if known)
   - **BDD Feature**: path to the feature file from Step 3
3. Review the generated `todo.md` and refine it:
   - Break large tasks into phases (Phase 1, Phase 2, etc.) under the Implementation section.
   - Each phase should be a cohesive unit of work that can be independently tested.
   - Add research items for any unknowns.
4. Review `doc.md` and populate the Open Questions section with anything unclear from the issue.
5. **If there are open questions that cannot be resolved by reading the codebase or documentation** → Pause and ask the user. Do NOT proceed with unresolved questions that could lead to wrong implementation choices.
6. Commit the nano-spec files:
   ```
   git add tasks/dev-loop-<issue-number>/
   git commit -m "docs: add nano-spec plan for #<number> [REQ-XXX]"
   ```
   Include `[REQ-XXX]` only if a REQ-ID is available.
7. Push the commit.

**If `--plan-only` is set, STOP HERE.** Report the following and exit:
- Issue number and title
- Branch name
- Nano-spec directory: `tasks/dev-loop-<issue-number>/`
- BDD feature file path
- Summary of planned phases from `todo.md` (phase names and descriptions)

---

### Step 5 — Implement Phases

**If `--implement-only` is set, start here.** First, recover state:
1. Read `tasks/dev-loop-<issue-number>/todo.md` to understand the implementation phases.
2. Read `tasks/dev-loop-<issue-number>/log.md` to understand what's been done so far.
3. Find and check out the existing branch: `git branch -a | grep dev-loop/<issue-number>` then `git checkout <branch>`.
4. Proceed with implementation.

For each phase defined in `todo.md`, execute the following sub-steps:

#### 5a. Research
- Read relevant documentation, explore the codebase, and resolve unknowns for this phase.
- If the project has existing patterns for what you're building, follow them.

#### 5b. Implement
- Write the code for this phase.
- Follow existing project conventions (code style, file organization, naming).
- Keep changes focused — only implement what's in the current phase.

#### 5c. JIT Test
- Run the jit-test agent on this phase's staged changes.
- If jit-test finds true bugs, fix them before proceeding.

#### 5d. Log
- Update nano-spec `log.md` with what was done in this phase via `/nano-spec update`.
- Check off completed items in `todo.md`.

#### 5e. Commit
- Stage and commit the phase's work:
  ```
  git add <changed-files>
  git commit -m "<type>: <description> (#<issue-number>) [REQ-XXX]"
  ```
  Use conventional commit types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`.
  Include `[REQ-XXX]` only if a REQ-ID is available from Step 1.
- Push after each phase commit.

Repeat for all phases.

---

### Step 6 — Automate BDD Tests

Turn the specification feature file into executable tests.

1. Invoke the `bdd-author` skill with action `automate`, passing the feature file path from Step 3.
2. Fill in the step definition bodies with real assertions based on the implementation from Step 5.
3. Commit the step definitions:
   ```
   git add <step-definitions-path>
   git commit -m "test: automate BDD step definitions for #<number>"
   ```
4. Push the commit.

---

### Step 7 — BDD Fix/Test Loop

Run BDD tests and iterate on failures.

1. Run the BDD tests using the project's test runner.
2. If all tests pass, proceed to Step 8.
3. If tests fail:
   a. Read the failure output carefully.
   b. Determine if the failure is in the test code or the implementation.
   c. Fix the issue.
   d. Re-run the tests.
   e. Repeat up to **5 iterations**.
4. If tests still fail after 5 iterations, pause and ask the user for guidance. Include:
   - The failing test(s) and their output
   - What you've tried so far
   - Your best guess at the root cause

---

### Step 8 — Full Test Suite

Run all project tests to catch regressions.

1. Detect the project's test runner (look for `pytest`, `npm test`, `cargo test`, `go test`, `mix test`, etc.).
2. Run the full test suite.
3. If all tests pass, proceed to Step 9.
4. If tests fail:
   a. Identify whether failures are caused by this PR's changes or are pre-existing.
   b. Fix failures caused by this PR.
   c. Re-run. Repeat up to 3 iterations.
   d. If pre-existing failures are the only remaining failures, note them and proceed.
5. Commit any fixes:
   ```
   git add <files>
   git commit -m "fix: address test failures for #<number>"
   ```
6. Push.

---

### Step 9 — Self-Review

Review the PR for quality before submission.

1. Invoke the self-review agent on the current PR diff.
2. Read the self-review report.
3. Address all **Critical** findings — these must be fixed.
4. Address **Suggestions** where the fix is straightforward and clearly beneficial.
5. For Suggestions you choose not to address, add a brief justification in the PR description.
6. Commit and push any fixes:
   ```
   git add <files>
   git commit -m "refactor: address self-review findings for #<number>"
   ```

---

### Step 10 — Submit for Review

Finalize the PR for human review.

1. Update the PR description with a comprehensive summary including full traceability:
   ```bash
   gh pr edit <pr-number> --body "$(cat <<'EOF'
   Closes #<issue-number>

   ## Traceability
   - **Requirement**: REQ-XXX (if available, otherwise omit this line)
   - **Issue**: #<issue-number>
   - **Phase**: <phase directory path> (if known from req-decompose footer, otherwise omit)
   - **Nano-spec**: `tasks/dev-loop-<issue-number>/`
   - **BDD Feature**: `<path to feature file>`

   ## Summary
   <bullet points of what was implemented>

   ## BDD Scenarios
   <list of scenarios from the feature file, with @AC-N tags>

   ## Test Results
   - BDD tests: <pass/fail>
   - Full suite: <pass/fail>

   ## Self-Review
   <summary of findings addressed>
   <any unaddressed suggestions with justification>

   ---
   Automated implementation by dev-loop agent.
   EOF
   )"
   ```
2. Mark the PR as ready:
   ```bash
   gh pr ready <pr-number>
   ```
3. Invoke `issue-pick` skill with action `complete <issue-number>` to update labels (remove `dev-loop-active`, add `dev-loop-review`).
4. Report the final status to the user with a link to the PR.
