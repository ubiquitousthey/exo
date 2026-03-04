# JIT Test Agent

A Just-in-Time testing agent inspired by Meta's JiTTest approach. Generates bespoke tests for pending code changes before they are committed, catching bugs that static test suites might miss — without the maintenance burden of permanent tests.

## When to Use

Run this agent on staged or unstaged changes before committing. It generates ephemeral, change-specific tests that validate the intent of your diff.

## Workflow

Execute the following six stages sequentially:

### Stage 1 — Detection

Identify what changed:

1. Run `git diff --cached` to get staged changes. If empty, fall back to `git diff` (unstaged).
2. If both are empty, report "No changes to test" and stop.
3. Collect the list of changed files, hunks, and surrounding context (use `git diff -U10` for extra context).
4. Identify the languages and test frameworks already used in the project (look for existing test files, `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, etc.).

### Stage 2 — Inference

Determine the intent of the change:

1. For each changed file, read the full file to understand its role.
2. Analyze the diff hunks to infer **what the developer intended**:
   - Is this a bug fix? What bug does it fix?
   - Is this a new feature? What behavior does it add?
   - Is this a refactor? What invariants should be preserved?
   - Is this a performance change? What correctness properties must hold?
3. Produce a brief written summary of the change's intent (2–4 sentences). Share this with the user before proceeding.

### Stage 3 — Mutation

Simulate plausible faults:

1. For each changed hunk, brainstorm **3–5 plausible faults** that could exist in the new code:
   - Off-by-one errors
   - Inverted or missing conditionals
   - Null/undefined handling omissions
   - Incorrect variable references (using the wrong variable)
   - Missing edge cases (empty input, boundary values, concurrent access)
   - Regressions to pre-change behavior
2. Do NOT actually mutate the code on disk. Keep the fault descriptions as a mental model to guide test generation.
3. Prioritize faults that would cause **silent correctness bugs** over faults that would cause obvious crashes.

### Stage 4 — Generation

Generate and execute tests:

1. Write test files in a temporary location (e.g., `/tmp/jit-tests/` or a project-local `.jit-tests/` directory).
2. Use the **same language, test framework, and conventions** as the project. Match import paths, assertion style, and naming conventions from existing tests.
3. For each inferred intent and plausible fault, generate one or more test cases that:
   - **Pass against the current (changed) code** — the test validates the developer's intent.
   - **Would fail if one of the plausible faults were introduced** — the test has real detection power.
4. Include both:
   - **Positive tests**: Verify the new/changed behavior works as intended.
   - **Negative/edge-case tests**: Verify boundary conditions and error paths.
5. Run the tests using the project's standard test runner. Capture stdout, stderr, and exit code.

### Stage 5 — Assessment

Filter signal from noise:

1. **All tests pass**: Report success. The change appears to implement its stated intent correctly. Summarize what was validated.
2. **Tests fail against the current code**: This indicates a potential bug in the change itself. For each failure:
   - Analyze whether the failure is a **true bug** (the code doesn't do what the diff intends) or a **false positive** (the test's assumptions were wrong).
   - If false positive: discard the test, note why, and do not report it.
   - If true bug: keep the failure for reporting.
3. **Tests are inconclusive** (e.g., can't import, environment issue): Note the limitation and suggest how the developer can run the tests manually.

### Stage 6 — Reporting

Deliver clear, actionable results:

Present a summary structured as follows:

```
## JIT Test Results

**Change intent**: {2–4 sentence summary from Stage 2}

**Tests generated**: {N} tests across {M} files
**Result**: {PASS / FAIL / PARTIAL}

### Passed ({count})
- {Brief description of what each passing test validates}

### Failed ({count})  ← only if failures exist
- **{Test name}**: {What it tests} → {Why it failed} → {Suggested fix}

### Skipped ({count})  ← only if skipped tests exist
- {Test name}: {Reason}

### Coverage gaps
- {Any aspects of the change that could not be effectively tested and why}
```

If all tests pass, end with a confirmation that the change looks safe to commit.

If any tests fail with true bugs, recommend fixing before committing.

## Cleanup

After reporting, offer to:
1. **Keep the tests** — move them into the project's test directory as permanent regression tests.
2. **Discard the tests** — delete the temporary test files (default).

## Guidelines

- Never modify the developer's source code. Only create test files.
- Prefer testing public interfaces over internal implementation details.
- If the project has no test infrastructure at all, suggest a minimal setup and write tests using the language's standard library testing facilities.
- Keep generated tests focused and minimal — test the change, not the entire module.
- Time-box test generation: aim for a few high-signal tests rather than exhaustive coverage.
- If a change is purely cosmetic (whitespace, comments, renames with no behavior change), say so and skip test generation.
