---
name: bdd-fix-loop
description: Run BDD tests and iterate on failures until they pass. Use "bdd-fix-loop run" to execute the test-fix cycle with up to 5 iterations.
---

# bdd-fix-loop: BDD Test Fix Loop

Run BDD tests and iterate on failures, fixing test code or implementation until all scenarios pass.

## Arguments
- $ACTION: The action to perform (run)
- $FEATURE_PATH: Path to the BDD feature file
- $ISSUE_NUMBER: The GitHub issue number (optional, for commit messages)

## Framework Detection

Detect the project's BDD test runner:
1. Check for `behave.ini`, `pytest.ini`/`pyproject.toml` with pytest-bdd config → use `pytest`
2. Check for `cucumber.js`, `.cucumber` config → use `npx cucumber-js`
3. Check for existing `*.feature` files and their associated step definitions to infer the runner
4. Fall back to the project's primary test runner with the feature file path

## Actions

### run

Run BDD tests and fix failures iteratively.

**Usage**: `bdd-fix-loop run`

**Steps:**

1. Detect the BDD test runner per the detection strategy above.
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

### Output Format (run)
```
BDD Tests: PASS | FAIL
Runner: <detected test runner>
Feature: <feature file path>
Scenarios: <passed>/<total>
Iterations: <N>
Failures: <summary of remaining failures, if any>
```
