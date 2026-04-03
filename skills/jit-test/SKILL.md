---
name: jit-test
description: Generate bespoke tests for pending code changes, catch bugs before commit, and promote durable tests into the permanent test suite. Use "jit-test run" to generate and execute tests, or "jit-test promote" to keep valuable tests.
---

# jit-test: Just-in-Time Testing

Generate bespoke tests for pending code changes before they are committed. Catches bugs that static test suites might miss. Classifies generated tests as ephemeral (diff-coupled, throw away) or durable (worth keeping as permanent regression tests).

## Arguments
- $ACTION: The action to perform (run, promote)
- $ISSUE_NUMBER: The GitHub issue number (optional, for commit messages when promoting)

## Actions

### run

Generate and execute tests for staged or unstaged changes. Classify each test for long-term value.

**Usage**: `jit-test run`

**Steps:**

#### 1. Detection
1. Run `git diff --cached` to get staged changes. If empty, fall back to `git diff` (unstaged).
2. If both are empty, report "No changes to test" and stop.
3. Collect the list of changed files, hunks, and surrounding context (use `git diff -U10` for extra context).
4. Identify the languages and test frameworks already used in the project.

#### 2. Inference
1. For each changed file, read the full file to understand its role.
2. Analyze the diff hunks to infer the developer's intent:
   - Bug fix? New feature? Refactor? Performance change?
3. Produce a brief written summary of the change's intent (2-4 sentences).

#### 3. Mutation
Brainstorm **3-5 plausible faults** per changed hunk (without actually mutating code):
- Off-by-one errors
- Inverted or missing conditionals
- Null/undefined handling omissions
- Incorrect variable references
- Missing edge cases (empty input, boundary values)
- Regressions to pre-change behavior

Prioritize faults that would cause **silent correctness bugs** over obvious crashes.

#### 4. Generation
1. Write test files in a temporary location (`.jit-tests/` directory).
2. Use the **same language, test framework, and conventions** as the project.
3. For each inferred intent and plausible fault, generate tests that:
   - **Pass against the current code** — validates the developer's intent
   - **Would fail if a plausible fault were introduced** — has real detection power
4. Include both positive tests and negative/edge-case tests.
5. Run the tests using the project's standard test runner.

#### 5. Assessment
1. **All pass**: Report success, summarize what was validated.
2. **Tests fail against current code**: Analyze each failure:
   - **True bug** in the change → keep the failure for reporting
   - **False positive** (wrong test assumptions) → discard, note why
3. **Inconclusive** (import errors, env issues) → note limitation, suggest manual run.

#### 6. Classification
Classify each generated test as **durable** or **ephemeral**:

**Durable** (worth keeping permanently):
- Tests a public function, method, or API endpoint
- Validates a boundary condition or edge case
- Exercises an error handling path
- Doesn't reference internal variable names or implementation details
- Would survive a refactor that preserves behavior

**Ephemeral** (throw away after this run):
- Asserts on specific line numbers or internal state
- Tests a private helper directly
- Tightly coupled to the specific diff structure
- Would break on a refactor even if behavior is preserved

#### 7. Reporting
Present results:

```
## JIT Test Results

**Change intent**: {2-4 sentence summary}

**Tests generated**: {N} tests across {M} files
**Result**: PASS | FAIL | PARTIAL

### Passed ({count})
- {Brief description of what each passing test validates}

### Failed ({count})  ← only if failures exist
- **{Test name}**: {What it tests} → {Why it failed} → {Suggested fix}

### Durable Tests ({count}) ← worth promoting
- **{Test name}** ({file}): {What it tests} — {Why it's durable}

### Ephemeral Tests ({count}) ← will be discarded
- **{Test name}**: {What it tests}

### Coverage gaps
- {Aspects of the change that could not be effectively tested}
```

If all tests pass and durable tests exist, recommend running `jit-test promote`.

### Output Format (run)
```
JIT Tests: PASS | FAIL | PARTIAL
Generated: <N> tests (<D> durable, <E> ephemeral)
Bugs found: <count>
Promote candidates: <count>
```

---

### promote

Move durable tests from the last JIT run into the project's permanent test suite.

**Usage**: `jit-test promote`

**Steps:**

1. Scan `.jit-tests/` for test files from the last run. If empty, report "No JIT tests to promote" and stop.
2. For each test classified as durable in the last run:
   a. Determine the correct destination in the project's test directory:
      - Match the project's test file naming conventions (e.g., `test_*.py`, `*.test.ts`, `*_test.go`)
      - Place in the same package/directory structure as the code under test
      - If a test file for the module already exists, append to it rather than creating a new file
   b. Adjust imports and paths to work from the permanent location (not `.jit-tests/`).
   c. Remove any JIT-specific scaffolding or comments.
   d. Add a brief comment noting the test's origin: `# Promoted from JIT test — validates <what it tests>`
3. Remove the promoted tests from `.jit-tests/`.
4. Clean up `.jit-tests/` — delete ephemeral tests and the directory if empty.
5. Commit the promoted tests:
   ```bash
   git add <promoted-test-files>
   git rm -r .jit-tests/ 2>/dev/null || true
   git commit -m "test: promote durable JIT tests for #$ISSUE_NUMBER"
   ```
   Include issue number only if $ISSUE_NUMBER is available.
6. Push the commit.

### Output Format (promote)
```
Promoted: <N> tests
Destinations:
  - <test-file-path>: <count> tests added
Discarded: <N> ephemeral tests
Commit: <sha>
```
