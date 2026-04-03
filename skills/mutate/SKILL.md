---
name: mutate
description: Run mutation testing to validate test suite quality. Use "mutate diff" for fast diff-scoped mutation testing, "mutate full" for comprehensive PR-level testing, or "mutate report" to generate a mutation testing report.
---

# mutate: Mutation Testing

Introduce small changes (mutants) to source code and check whether the test suite catches them. Measures test quality — not just coverage, but detection power. Supports diff-scoped testing for fast feedback and full-scope testing for comprehensive quality assessment.

## Arguments
- $ACTION: The action to perform (diff, full, report)
- $BASE_REF: Git ref to diff against (default: `HEAD~1` for diff, `main` for full)
- $TEST_COMMAND: Override the test command (optional, auto-detected if omitted)
- $TEST_FILES: Specific test files to run against mutants (optional, used by jit-test for targeted verification)

## Framework Detection

Detect the project's language and select the appropriate mutation testing tool:

| Language | Tool | Install |
|----------|------|---------|
| Python | `mutmut` | `pip install mutmut` |
| JavaScript/TypeScript | `stryker` | `npm install --save-dev @stryker-mutator/core` |
| Java/Kotlin | `pitest` | Maven/Gradle plugin |
| Rust | `cargo-mutants` | `cargo install cargo-mutants` |
| Go | `gremlins` | `go install github.com/go-gremlins/gremlins/cmd/gremlins@latest` |

Detection order:
1. Check for existing mutation testing config (`.mutmut`, `stryker.conf.*`, `pitest` in pom.xml/build.gradle)
2. Infer from project language markers (`pyproject.toml` → Python, `package.json` → JS/TS, etc.)
3. If the tool is not installed, report what to install and stop.

## Mutant Classification

After running mutations, classify each survived mutant:

**Actionable** (test gap — should add or improve a test):
- The mutation changes observable behavior (return value, side effect, output)
- No existing test validates this behavior
- A test could reasonably be written to catch it

**Equivalent** (mutation doesn't change behavior — ignore):
- The mutation produces the same result (e.g., reordering commutative operations)
- Dead code paths
- Optimization-only changes with identical output

## Actions

### diff

Lightweight, diff-scoped mutation testing. Mutates only lines changed in the current diff. Fast enough for per-phase use inside the dev-loop.

**Usage**: `mutate diff [--base HEAD~1]`

**Steps:**

1. Detect the mutation testing framework.
2. Get the changed lines:
   ```bash
   git diff $BASE_REF --unified=0
   ```
3. Parse the diff to extract changed file paths and line ranges.
4. Filter to only source files (exclude tests, configs, docs).
5. Configure the mutation tool to target only the changed lines:
   - **mutmut**: `mutmut run --paths-to-mutate <files> --lines <ranges>`
   - **stryker**: Configure `mutate` array in temp config to target specific files/lines
   - **cargo-mutants**: `cargo mutants --file <files> --line <ranges>`
   - **pitest**: Configure `targetClasses` and line filters
6. If $TEST_FILES is provided, run only those tests against mutants. Otherwise use $TEST_COMMAND or the auto-detected test command.
7. Run the mutation tests.
8. Classify survived mutants as actionable or equivalent.
9. Report results.

### Output Format (diff)
```
Mutation Testing (diff-scoped):
  Files mutated: <N>
  Lines in scope: <N>
  Mutants generated: <N>
  Killed: <N> (<percentage>%)
  Survived: <N> (<actionable count> actionable, <equivalent count> equivalent)
  Timeout: <N>
  Mutation score: <percentage>%

Survived mutants:
  - [file:line] <mutation description> — <actionable | equivalent>
    Suggestion: <what test to add or improve>
```

---

### full

Comprehensive mutation testing on all files changed in a PR or branch vs base. Suited for CI or standalone quality assessment.

**Usage**: `mutate full [--base main]`

**Steps:**

1. Detect the mutation testing framework.
2. Get all files changed between $BASE_REF and HEAD:
   ```bash
   git diff --name-only $BASE_REF...HEAD
   ```
3. Filter to source files only.
4. Configure the mutation tool to target all changed source files (no line restriction).
5. Run the full test suite against each mutant (use $TEST_COMMAND or auto-detect).
6. Classify survived mutants.
7. Report results.

**Performance notes:**
- This can be slow for large PRs. The tool will report estimated time before starting.
- Most mutation tools support parallelism — use it (e.g., `mutmut --runners <N>`, Stryker's `concurrency`).
- For very large diffs (>500 lines changed), suggest using `diff` action on specific files instead.

### Output Format (full)
```
Mutation Testing (full scope):
  Files mutated: <N>
  Mutants generated: <N>
  Killed: <N> (<percentage>%)
  Survived: <N> (<actionable count> actionable, <equivalent count> equivalent)
  Timeout: <N>
  Mutation score: <percentage>%
  Duration: <time>

Survived mutants (actionable):
  - [file:line] <mutation description>
    Suggestion: <what test to add or improve>

Equivalent mutants (no action needed): <N>

Quality assessment:
  - <High/Medium/Low> test quality for changed code
  - <Specific recommendations>
```

---

### report

Generate a human-readable mutation testing report from the last run's results.

**Usage**: `mutate report`

**Steps:**

1. Locate the mutation tool's results:
   - **mutmut**: `.mutmut-cache/`
   - **stryker**: `reports/mutation/`
   - **pitest**: `target/pit-reports/`
   - **cargo-mutants**: `mutants.out/`
2. Parse the results.
3. Generate a markdown report organized by file, then by severity:

```markdown
# Mutation Testing Report

## Summary
- **Mutation score**: <percentage>%
- **Mutants**: <killed>/<total> killed
- **Quality**: <High/Medium/Low>

## Actionable Survived Mutants

### <file-path>
| Line | Mutation | Suggestion |
|------|----------|------------|
| <N> | <description> | <what test to add> |

## Equivalent Mutants (ignored)
<count> mutants classified as equivalent (no behavior change).

## Recommendations
- <Prioritized list of test improvements>
```

4. If invoked with a destination path, write the report there. Otherwise print to stdout.

### Output Format (report)
```
Report generated: <path or "stdout">
Mutation score: <percentage>%
Actionable gaps: <N>
```
