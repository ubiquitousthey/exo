---
name: implement-phases
description: Execute nano-spec implementation phases with research, coding, JIT testing, logging, and commits. Use "implement-phases run" to execute all phases, or "implement-phases resume" to pick up from the last completed phase.
---

# implement-phases: Phased Implementation

Execute the implementation phases defined in a nano-spec `todo.md`, with research, coding, JIT testing, progress logging, and per-phase commits.

## Arguments
- $ACTION: The action to perform (run, resume)
- $NANO_SPEC_PATH: Path to the nano-spec task directory (e.g., `tasks/user-authentication/`)
- $ISSUE_NUMBER: The GitHub issue number (for commit messages)
- $REQ_ID: Requirement ID like REQ-001 (optional, for commit messages)
- $DESIGN_PATHS: Comma-separated list of design file paths (optional, for UI implementation reference)

## Actions

### run

Execute all implementation phases from the beginning.

**Usage**: `implement-phases run`

**Steps:**

1. Read `$NANO_SPEC_PATH/todo.md` to understand the implementation phases.
2. Read `$NANO_SPEC_PATH/log.md` to understand what's been done so far.
3. If $DESIGN_PATHS is provided, read the design files to understand the target visual implementation.
4. For each phase defined in `todo.md`, execute the sub-steps below.

#### Per-Phase Sub-steps

##### a. Research
- Read relevant documentation, explore the codebase, and resolve unknowns for this phase.
- If the project has existing patterns for what you're building, follow them.

##### b. Implement
- Write the code for this phase.
- Follow existing project conventions (code style, file organization, naming).
- Keep changes focused — only implement what's in the current phase.

##### c. JIT Test
- Invoke the `jit-test` skill with action `run` on this phase's staged changes.
- If jit-test finds true bugs, fix them before proceeding.
- jit-test automatically verifies durable tests via mutation testing (if a mutation tool is available), strengthening assertions where needed.
- If jit-test identifies durable tests worth keeping, invoke `jit-test promote` to move them into the project's permanent test suite.

##### d. Log
- Update nano-spec `log.md` with what was done in this phase via the `nano-spec` skill (`update` action).
- Check off completed items in `todo.md`.

##### e. Commit
- Stage and commit the phase's work:
  ```bash
  git add <changed-files>
  git commit -m "<type>: <description> (#$ISSUE_NUMBER) [$REQ_ID]"
  ```
  Use conventional commit types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`.
  Include `[$REQ_ID]` only if $REQ_ID is available.
- Push after each phase commit.

Repeat for all phases.

### Output Format (run)
```
Phases completed: <N>/<total>
Commits:
  - <sha>: <commit message>
  - <sha>: <commit message>
Files changed: <count>
```

---

### resume

Pick up implementation from the last completed phase.

**Usage**: `implement-phases resume`

**Steps:**

1. Read `$NANO_SPEC_PATH/todo.md` to identify which phases are already checked off.
2. Read `$NANO_SPEC_PATH/log.md` to understand what was done in completed phases.
3. Identify the first unchecked phase and begin execution from there.
4. Execute the same per-phase sub-steps as `run` for all remaining phases.

### Output Format (resume)
```
Resumed from: Phase <N> (<phase name>)
Phases completed: <completed>/<total>
Commits:
  - <sha>: <commit message>
Files changed: <count>
```
