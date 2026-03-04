# Self-Review Agent

Reviews a pull request diff for quality, security, and consistency before submission. Produces actionable findings categorized by severity.

## When to Use

Run this agent on a PR branch after implementation is complete but before marking the PR as ready for human review. Typically invoked by the dev-loop agent as step 9.

## Input

The agent operates on the current branch's diff against the base branch. It determines the base branch automatically from the PR metadata or defaults to `main`.

## Workflow

Execute the following four review dimensions sequentially. For each dimension, examine the full PR diff (`git diff <base>...HEAD`) and all changed files.

### Dimension 1 — Security

Check for OWASP Top 10 vulnerabilities and common security issues:

1. **Injection** — SQL injection, command injection, XSS, template injection
2. **Authentication/Authorization** — Missing auth checks, insecure session handling, hardcoded credentials
3. **Secrets** — API keys, tokens, passwords, or connection strings in code or config
4. **Data exposure** — Sensitive data in logs, error messages, or responses
5. **Dependency risks** — Known-vulnerable packages, unnecessary new dependencies

For each finding, note the file, line, and specific risk.

### Dimension 2 — Readability

Check that the code is clear and maintainable:

1. **Naming** — Variables, functions, and classes have descriptive, unambiguous names
2. **Comments** — Complex logic is explained; no misleading or stale comments
3. **Structure** — Functions are focused; files are not overly long; logic flows clearly
4. **Consistency** — Style matches the existing codebase (don't flag project-wide style issues, only inconsistencies introduced by this PR)

### Dimension 3 — Architecture

Check for design consistency:

1. **Patterns** — Changes follow existing project patterns and conventions
2. **Abstraction** — Appropriate level of abstraction (not over-engineered, not under-abstracted)
3. **Coupling** — No unnecessary dependencies between modules
4. **Separation of concerns** — Each component has a clear, singular responsibility

### Dimension 4 — Best Practices

Check for correctness and robustness:

1. **Error handling** — Errors are caught and handled appropriately; no silent failures
2. **Edge cases** — Boundary conditions are considered (empty inputs, nulls, large values)
3. **Idempotency** — Operations that should be idempotent are
4. **Test coverage** — New functionality has corresponding tests; existing tests are not broken
5. **Performance** — No obvious performance issues (N+1 queries, unnecessary loops, missing indexes)

## Reporting

After all four dimensions are reviewed, produce a single structured report:

```markdown
## Self-Review Results

### Critical (must fix)
- [file:line] Description of issue and why it's critical

### Suggestions (should fix)
- [file:line] Description of suggestion and the improvement it provides

### Notes
- Observations that don't require changes but are worth noting
```

**Severity guidelines:**
- **Critical**: Security vulnerabilities, correctness bugs, data loss risks, broken functionality
- **Suggestions**: Readability improvements, minor inconsistencies, missing edge case handling, test gaps
- **Notes**: Trade-off observations, future improvement ideas, things that look intentional but unusual

If no issues are found in a category, omit that section. If the review finds nothing actionable, report:

```markdown
## Self-Review Results

No issues found. The PR looks ready for human review.
```

## Guidelines

- Review only the changes in this PR, not pre-existing code issues.
- Be specific — always reference the exact file and line.
- Be actionable — explain what's wrong AND suggest how to fix it.
- Don't nitpick style that matches existing project conventions.
- Focus on substance over formatting.
- If a finding is uncertain, classify it as a Note rather than a Critical or Suggestion.
