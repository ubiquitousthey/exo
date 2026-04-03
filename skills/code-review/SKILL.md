---
name: code-review
description: Review code for quality, security, and consistency. Use "code-review self" to review your own PR before submission, or "code-review pr" to review any PR by number and post findings as a comment.
---

# code-review: Code Review

Review code changes for security, readability, architecture, and best practices. Can review your own PR (self-review before submission) or any PR by number (peer review with findings posted as a comment).

## Arguments
- $ACTION: The action to perform (self, pr)
- $PR_NUMBER: The pull request number (required for `pr`, optional for `self` — auto-detects from current branch)
- $REPO: Repository in owner/repo format (optional, defaults to current repo)

## Review Dimensions

Both actions apply the same four review dimensions:

### Dimension 1 — Security
Check for OWASP Top 10 vulnerabilities and common security issues:
1. **Injection** — SQL injection, command injection, XSS, template injection
2. **Authentication/Authorization** — Missing auth checks, insecure session handling, hardcoded credentials
3. **Secrets** — API keys, tokens, passwords, or connection strings in code or config
4. **Data exposure** — Sensitive data in logs, error messages, or responses
5. **Dependency risks** — Known-vulnerable packages, unnecessary new dependencies

### Dimension 2 — Readability
Check that the code is clear and maintainable:
1. **Naming** — Variables, functions, and classes have descriptive, unambiguous names
2. **Comments** — Complex logic is explained; no misleading or stale comments
3. **Structure** — Functions are focused; files are not overly long; logic flows clearly
4. **Consistency** — Style matches the existing codebase (only flag inconsistencies introduced by this PR)

### Dimension 3 — Architecture
Check for design consistency:
1. **Patterns** — Changes follow existing project patterns and conventions
2. **Abstraction** — Appropriate level (not over-engineered, not under-abstracted)
3. **Coupling** — No unnecessary dependencies between modules
4. **Separation of concerns** — Each component has a clear, singular responsibility

### Dimension 4 — Best Practices
Check for correctness and robustness:
1. **Error handling** — Errors are caught and handled appropriately; no silent failures
2. **Edge cases** — Boundary conditions are considered (empty inputs, nulls, large values)
3. **Idempotency** — Operations that should be idempotent are
4. **Test coverage** — New functionality has corresponding tests; existing tests are not broken
5. **Performance** — No obvious performance issues (N+1 queries, unnecessary loops, missing indexes)

## Severity Guidelines
- **Critical**: Security vulnerabilities, correctness bugs, data loss risks, broken functionality
- **Suggestions**: Readability improvements, minor inconsistencies, missing edge case handling, test gaps
- **Notes**: Trade-off observations, future improvement ideas, things that look intentional but unusual

## Actions

### self

Review your own PR diff before submission. Produces a structured report for the caller (typically the dev-loop agent) to act on.

**Usage**: `code-review self`

**Steps:**

1. Determine the base branch:
   - If $PR_NUMBER is provided, get the base from `gh pr view $PR_NUMBER --json baseRefName`.
   - Otherwise, detect the current branch's PR via `gh pr view --json number,baseRefName` or default to `main`.
2. Get the full diff:
   ```bash
   git diff <base>...HEAD
   ```
3. Read all changed files in full to understand context.
4. Execute the four review dimensions sequentially against the diff.
5. Produce the report.

**Review only changes in this PR**, not pre-existing code issues. Be specific (file and line), be actionable (explain what's wrong AND suggest a fix). Don't nitpick style that matches existing project conventions.

### Output Format (self)
```markdown
## Self-Review Results

### Critical (must fix)
- [file:line] Description of issue and why it's critical

### Suggestions (should fix)
- [file:line] Description of suggestion and the improvement it provides

### Notes
- Observations that don't require changes but are worth noting
```

If no issues found:
```markdown
## Self-Review Results

No issues found. The PR looks ready for human review.
```

---

### pr

Review any PR by number and post findings as a PR comment.

**Usage**: `code-review pr <number>`

**Steps:**

1. Fetch the PR diff:
   ```bash
   gh pr diff $PR_NUMBER
   ```
   Add `--repo $REPO` if provided.
2. Fetch PR metadata for context:
   ```bash
   gh pr view $PR_NUMBER --json title,body,files
   ```
3. Read all changed files in full to understand context.
4. Execute the four review dimensions sequentially against the diff.
5. Build the review comment and post it:
   ```bash
   gh pr comment $PR_NUMBER --body "$(cat <<'EOF'
   ## Code Review

   ### Critical (must fix)
   - [file:line] Description

   ### Suggestions (should fix)
   - [file:line] Description

   ### Notes
   - Observations

   ---
   Automated review by code-review skill.
   EOF
   )"
   ```
   Add `--repo $REPO` if provided.

### Output Format (pr)
```
Review posted on PR #<number>
Critical: <count>
Suggestions: <count>
Notes: <count>
```
