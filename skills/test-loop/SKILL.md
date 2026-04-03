---
name: test-loop
description: Run tests and iterate on failures. Use "test-loop bdd" to run BDD tests with a fix loop, or "test-loop full" to run the full project test suite and fix regressions.
---

# test-loop: Test Execution with Fix Loops

Run tests and iterate on failures, fixing test code or implementation until tests pass. Supports both BDD-specific test runs and full project test suites.

## Arguments
- $ACTION: The action to perform (bdd, full)
- $FEATURE_PATH: Path to the BDD feature file (required for `bdd`)
- $ISSUE_NUMBER: The GitHub issue number (optional, for commit messages)

## Runner Detection

### BDD Runner
Detect the project's BDD test runner:
1. Check for `behave.ini`, `pytest.ini`/`pyproject.toml` with pytest-bdd config → use `pytest`
2. Check for `cucumber.js`, `.cucumber` config → use `npx cucumber-js`
3. Check for existing `*.feature` files and their associated step definitions to infer the runner
4. Fall back to the project's primary test runner with the feature file path

### Full Suite Runner
Detect the project's test runner by checking (in order):
1. `pyproject.toml` or `pytest.ini` → `pytest`
2. `package.json` with `test` script → `npm test`
3. `Cargo.toml` → `cargo test`
4. `go.mod` → `go test ./...`
5. `mix.exs` → `mix test`
6. `Makefile` with `test` target → `make test`
7. Fall back to searching for test files and inferring the runner

## Actions

### bdd

Run BDD tests and fix failures iteratively.

**Usage**: `test-loop bdd`

**Steps:**

1. Detect the BDD test runner.
2. Run the BDD tests targeting $FEATURE_PATH:
   ```bash
   <test-runner> <feature-path-or-equivalent>
   ```
3. If all tests pass, report success and stop.
4. If tests fail:
   a. Read the failure output carefully.
   b. Determine if the failure is in the **test code** (step definitions, fixtures) or the **implementation** (application code).
   c. Fix the identified issue.
   d. Re-run the tests.
   e. Repeat up to **5 iterations**.
5. If tests still fail after 5 iterations, pause and ask the user for guidance. Include:
   - The failing test(s) and their output
   - What was tried in each iteration
   - Best guess at the root cause

### Output Format (bdd)
```
BDD Tests: PASS | FAIL
Runner: <detected test runner>
Feature: <feature file path>
Scenarios: <passed>/<total>
Iterations: <N>
Failures: <summary of remaining failures, if any>
```

---

### full

Run the project's full test suite and fix regressions caused by current changes.

**Usage**: `test-loop full`

**Steps:**

1. Detect the project's test runner.
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

### Output Format (full)
```
Test Suite: PASS | FAIL | PASS (with pre-existing failures)
Runner: <detected test runner>
Tests: <passed>/<total>
Iterations: <N>
Pre-existing failures: <count or "none">
Fixes committed: <sha or "none">
```
