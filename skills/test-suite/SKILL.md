---
name: test-suite
description: Run the project's full test suite and fix regressions caused by current changes. Use "test-suite run" to detect the test runner, execute all tests, and iterate on failures.
---

# test-suite: Full Test Suite Runner

Detect and run the project's full test suite, distinguishing between regressions caused by the current PR and pre-existing failures.

## Arguments
- $ACTION: The action to perform (run)
- $ISSUE_NUMBER: The GitHub issue number (optional, for commit messages)

## Test Runner Detection

Detect the project's test runner by checking (in order):
1. `pyproject.toml` or `pytest.ini` → `pytest`
2. `package.json` with `test` script → `npm test`
3. `Cargo.toml` → `cargo test`
4. `go.mod` → `go test ./...`
5. `mix.exs` → `mix test`
6. `Makefile` with `test` target → `make test`
7. Fall back to searching for test files and inferring the runner

## Actions

### run

Run the full test suite and fix regressions.

**Usage**: `test-suite run`

**Steps:**

1. Detect the project's test runner per the detection strategy above.
2. Run the full test suite:
   ```bash
   <detected-test-command>
   ```
3. If all tests pass, report success and stop.
4. If tests fail:
   a. Identify whether failures are caused by this PR's changes or are pre-existing:
      - Check `git stash && <test-command>` to see if failures exist on the base code (if practical)
      - Or analyze the failure messages and changed files to determine causation
   b. Fix failures caused by this PR's changes.
   c. Re-run. Repeat up to **3 iterations**.
   d. If pre-existing failures are the only remaining failures, note them and report success with caveats.
5. Commit any fixes:
   ```bash
   git add <files>
   git commit -m "fix: address test failures for #$ISSUE_NUMBER"
   ```
6. Push the commit.

### Output Format (run)
```
Test Suite: PASS | FAIL | PASS (with pre-existing failures)
Runner: <detected test runner>
Tests: <passed>/<total>
Iterations: <N>
Pre-existing failures: <count or "none">
Fixes committed: <sha or "none">
```
