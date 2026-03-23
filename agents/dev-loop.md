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
- **BDD test loop** → Max 5 fix iterations, then pause for help.

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
4. **Check for review gate feedback.** Read PR comments since the review gate post:
   ```bash
   gh pr view <pr-number> --comments --json comments
   ```
   - If feedback was left (not just `lgtm`), incorporate changes into the nano-spec and/or BDD feature file. Commit and push the updates.
   - If no approval comment (`lgtm`) is found, warn the user that the review gate hasn't been approved yet and ask whether to proceed anyway.
5. Remove the `dev-loop-review-gate` label:
   ```bash
   gh pr edit <pr-number> --remove-label dev-loop-review-gate
   ```
6. Skip directly to **Step 6 — Implement Phases** and continue from there.

If the nano-spec task directory doesn't exist, report an error and stop.

## Workflow

Execute the following 12 steps sequentially. After each step, update the nano-spec `log.md` with what was done. If `--resume` was provided, skip to Step 6.

**When `--plan-only` is set, execute ONLY steps 1-5, then stop.**
**When `--implement-only` is set, skip steps 1-5, execute steps 6-11.**

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
6. **Derive the feature slug:** Generate a kebab-case slug from the issue title (max 50 chars). Strip any `REQ-XXX:` prefix before slugifying. Examples: "Add user authentication" → `user-authentication`, "REQ-003: Fix payment retry logic" → `fix-payment-retry-logic`. This slug is used for the task directory, branch name, and all references throughout the workflow.
7. **Extract traceability identifiers:**
   - If the issue title matches `REQ-XXX: Title` (created by req-decompose), extract and store the REQ-ID (e.g., `REQ-001`).
   - If the issue body contains a `<!-- req-decompose source_req: REQ-XXX phase_dir: path -->` footer, extract and store the source REQ-ID and phase directory.
   - These identifiers are threaded through all subsequent steps.

---

### Step 2 — Plan with nano-spec

Create a detailed implementation plan with traceability.

1. Invoke `/nano-spec create <feature-slug> "<issue title>: <issue body summary>"`.
2. **Populate the Traceability section** in the generated `README.md`:
   - **Source**: `#<issue-number>` (and `REQ-XXX` if available, linking to the phase directory if known)
   - **BDD Feature**: *(to be populated after Step 4)*
3. Review the generated `todo.md` and refine it:
   - Break large tasks into phases (Phase 1, Phase 2, etc.) under the Implementation section.
   - Each phase should be a cohesive unit of work that can be independently tested.
   - Add research items for any unknowns.
4. Review `doc.md` and populate the Open Questions section with anything unclear from the issue.
5. **If there are open questions that cannot be resolved by reading the codebase or documentation** → Pause and ask the user. Do NOT proceed with unresolved questions that could lead to wrong implementation choices.

---

### Step 3 — Create Branch & Draft PR

Set up the working branch and create a draft PR.

1. Use the branch name `dev-loop/<issue-number>-<feature-slug>` with the slug derived in Step 1.
2. Create and checkout the branch:
   ```bash
   git checkout -b dev-loop/<issue-number>-<feature-slug>
   ```
3. Push the branch:
   ```bash
   git push -u origin dev-loop/<issue-number>-<feature-slug>
   ```
4. Create a draft PR linking to the issue:
   ```bash
   gh pr create --draft --title "<issue title>" --body "Closes #<number>\n\nAutomated implementation by dev-loop agent."
   ```
   Add `--repo` if specified.
5. Commit the nano-spec files from Step 2:
   ```
   git add tasks/<feature-slug>/
   git commit -m "docs: add nano-spec plan for #<number> [REQ-XXX]"
   ```
   Include `[REQ-XXX]` only if a REQ-ID is available.
6. Push the commit.

---

### Step 4 — Write BDD Test Spec

Generate a BDD feature file from the issue's acceptance criteria.

1. Invoke the `bdd-author` skill with action `write`, passing:
   - The issue title and body as context
   - The issue number (for `@issue-N` tag)
   - The REQ-ID if extracted in Step 1 (for `@REQ-XXX` tag)
2. Review the generated feature file to ensure:
   - Scenarios align with the issue's acceptance criteria
   - Traceability tags are present (`@REQ-XXX @issue-N` on the Feature line, `@AC-N` on each scenario)
3. Store the feature file path for use in subsequent steps (PR description, proof).
4. **Update the nano-spec** `README.md` Traceability section with the BDD feature file path.
5. Commit the feature file and the nano-spec update:
   ```
   git add <feature-file-path> tasks/<feature-slug>/README.md
   git commit -m "test: add BDD feature spec for #<number> [REQ-XXX]"
   ```
   Include `[REQ-XXX]` in the commit message only if a REQ-ID is available.
6. Push the commit.

---

### Step 5 — UI Design (Conditional)

If the feature involves UI work, generate designs with superdesign before the review gate so reviewers can assess the visual direction alongside the plan.

#### Detection

Determine if the feature requires UI work by checking:

1. **Explicit design reference**: If the GitHub issue body contains a link to an existing superdesign file (e.g., a path like `.superdesign/design_iterations/*.html` or a reference to a superdesign project), use that design directly — skip generation and proceed to step 5d.
2. **Issue signals**: The issue title or body mentions UI, frontend, page, screen, dashboard, form, component, layout, modal, dialog, widget, or similar visual terms.
3. **Project signals**: The project's `CLAUDE.md` references superdesign, or a `.superdesign/` directory exists in the project.
4. **BDD signals**: The BDD feature file from Step 4 contains scenarios involving user-visible interactions (clicking, viewing, navigating, filling forms).

If none of these signals are present, **skip this step entirely** and proceed to the Review Gate.

#### 5a. Check Prerequisites

Verify superdesign is available:
- Check if the project's `CLAUDE.md` has superdesign configuration or rules.
- Check if a `.superdesign/` directory exists in the project.
- If neither exists, note in `log.md` that superdesign is not configured for this project and skip this step.

#### 5b. Gather Design Context

Collect inputs for the design prompt:
- The issue title and acceptance criteria
- Relevant BDD scenarios (especially those describing what the user should see)
- Existing UI patterns in the project (scan for similar pages/components)
- Any design references or mockup links in the issue body

#### 5c. Generate Designs

Invoke superdesign to generate UI designs:
1. Craft a design prompt from the gathered context, describing the screen(s) or component(s) needed.
2. Use superdesign to generate designs. Superdesign creates HTML files in `.superdesign/design_iterations/` with Tailwind CSS styling.
3. Designs are generated as `{design_name}_{n}.html` files with variations for review.

#### 5d. Update Nano-spec with Designs

1. Add a **UI Design** section to the nano-spec `README.md` documenting:
   - Design file paths (relative to project root)
   - Brief description of what each design shows
   - If an existing design was referenced from the issue, note it as the source design
2. Update `todo.md` implementation phases to reference the designs — add notes about which design to implement in the relevant phase.
3. Commit the designs and nano-spec updates:
   ```
   git add .superdesign/design_iterations/ tasks/<feature-slug>/
   git commit -m "design: add superdesign UI mockups for #<number> [REQ-XXX]"
   ```
   Include `[REQ-XXX]` only if a REQ-ID is available.
4. Push the commit.

---

### Review Gate

**Post the plan and BDD spec as a PR comment for human review, then stop.**

1. Build a summary comment containing:
   - The nano-spec plan (`tasks/<feature-slug>/README.md` contents — background, goals, scope)
   - The phased implementation plan (`todo.md` contents)
   - The BDD feature file contents
   - UI design file paths and descriptions (if Step 5 generated designs)
   - Any open questions from `doc.md`
   - A note: *"Reply to this comment with feedback, or approve by commenting `lgtm`. Then resume with `/dev-loop --resume <feature-slug>`."*

2. Post the comment on the draft PR:
   ```bash
   gh pr comment <pr-number> --body "$(cat <<'EOF'
   ## 📋 Review Gate — Plan & BDD Spec

   ### Nano-spec Plan
   <README.md contents>

   ### Implementation Phases
   <todo.md contents>

   ### BDD Feature Spec
   ```gherkin
   <feature file contents>
   ```

   ### UI Designs
   <If Step 5 produced designs, list design file paths and descriptions from the nano-spec UI Design section. If no designs, omit this section.>

   ### Open Questions
   <open questions from doc.md, or "None">

   ---
   **Please review the plan and BDD spec above.**
   - Reply with feedback to request changes.
   - Comment `lgtm` to approve.

   Then resume implementation with:
   ```
   /dev-loop --resume <feature-slug>
   ```
   EOF
   )"
   ```

3. Add a `dev-loop-review-gate` label to the PR:
   ```bash
   gh pr edit <pr-number> --add-label dev-loop-review-gate
   ```

4. Report to the user that the review gate has been posted and provide the PR link. **Stop execution.** Do NOT proceed to Step 6.

The user will review on GitHub, leave feedback or approve, then invoke `/dev-loop --resume <feature-slug>` to continue from Step 6.

**If `--plan-only` is set, STOP HERE.** Report the following and exit:
- Issue number and title
- Branch name
- Nano-spec directory: `tasks/dev-loop-<issue-number>/`
- BDD feature file path
- UI design file paths (if Step 5 generated designs)
- Summary of planned phases from `todo.md` (phase names and descriptions)

---

### Step 6 — Implement Phases

**If `--implement-only` is set, start here.** First, recover state:
1. Read `tasks/dev-loop-<issue-number>/todo.md` to understand the implementation phases.
2. Read `tasks/dev-loop-<issue-number>/log.md` to understand what's been done so far.
3. Find and check out the existing branch: `git branch -a | grep dev-loop/<issue-number>` then `git checkout <branch>`.
4. If the nano-spec `README.md` has a UI Design section, read the referenced design files to understand the target visual implementation.
5. Proceed with implementation.

For each phase defined in `todo.md`, execute the following sub-steps:

#### 6a. Research
- Read relevant documentation, explore the codebase, and resolve unknowns for this phase.
- If the project has existing patterns for what you're building, follow them.

#### 6b. Implement
- Write the code for this phase.
- Follow existing project conventions (code style, file organization, naming).
- Keep changes focused — only implement what's in the current phase.

#### 6c. JIT Test
- Run the jit-test agent on this phase's staged changes.
- If jit-test finds true bugs, fix them before proceeding.

#### 6d. Log
- Update nano-spec `log.md` with what was done in this phase via `/nano-spec update`.
- Check off completed items in `todo.md`.

#### 6e. Commit
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

### Step 7 — Automate BDD Tests

Turn the specification feature file into executable tests.

1. Invoke the `bdd-author` skill with action `automate`, passing the feature file path from Step 4.
2. Fill in the step definition bodies with real assertions based on the implementation from Step 6.
3. Commit the step definitions:
   ```
   git add <step-definitions-path>
   git commit -m "test: automate BDD step definitions for #<number>"
   ```
4. Push the commit.

---

### Step 8 — BDD Fix/Test Loop

Run BDD tests and iterate on failures.

1. Run the BDD tests using the project's test runner.
2. If all tests pass, proceed to Step 9.
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

### Step 9 — Full Test Suite

Run all project tests to catch regressions.

1. Detect the project's test runner (look for `pytest`, `npm test`, `cargo test`, `go test`, `mix test`, etc.).
2. Run the full test suite.
3. If all tests pass, proceed to Step 10.
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

### Step 10 — Self-Review

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

### Step 11 — Generate Proof

Create an executable proof document demonstrating the feature works.

1. Invoke the `showboat-proof` skill with action `prove`, passing:
   - The issue title and body as feature context
   - The BDD feature file path from Step 4 (so proof sections map to acceptance criteria)
   - The REQ-ID and issue number for traceability
2. If the implementation includes a web UI, the skill will use rodney for browser automation and screenshots. Otherwise it will use CLI commands and captured output.
3. Review the generated proof document to ensure it meaningfully demonstrates the feature — not just "it runs without errors."
4. Commit the proof:
   ```
   git add proofs/<feature-slug>/
   git commit -m "docs: add showboat proof for #<number> [REQ-XXX]"
   ```
   Include `[REQ-XXX]` only if a REQ-ID is available.
5. Push the commit.

---

### Step 12 — Submit for Review

Finalize the PR for human review.

1. Update the PR description with a comprehensive summary including full traceability:
   ```bash
   gh pr edit <pr-number> --body "$(cat <<'EOF'
   Closes #<issue-number>

   ## Traceability
   - **Requirement**: REQ-XXX (if available, otherwise omit this line)
   - **Issue**: #<issue-number>
   - **Phase**: <phase directory path> (if known from req-decompose footer, otherwise omit)
   - **Nano-spec**: `tasks/<feature-slug>/`
   - **BDD Feature**: `<path to feature file>`
   - **Proof**: `proofs/<feature-slug>/README.md`

   ## Summary
   <bullet points of what was implemented>

   ## BDD Scenarios
   <list of scenarios from the feature file, with @AC-N tags>

   ## Test Results
   - BDD tests: <pass/fail>
   - Full suite: <pass/fail>

   ## Proof
   - Proof document: `proofs/<feature-slug>/README.md`
   - Re-verify with: `showboat verify proofs/<feature-slug>/README.md`

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
