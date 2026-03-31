---
name: branch-pr
description: Create a git branch and draft PR from issue context. Use "branch-pr create" to set up a working branch with a draft PR, or "branch-pr push" to push the current branch.
---

# branch-pr: Branch & Draft PR Creation

Set up a working branch and draft pull request for a GitHub issue.

## Arguments
- $ACTION: The action to perform (create, push)
- $ISSUE_NUMBER: The GitHub issue number
- $FEATURE_SLUG: Kebab-case feature name (used in branch name and task directory)
- $ISSUE_TITLE: The issue title (used in PR title)
- $REPO: Repository in owner/repo format (optional, defaults to current repo)
- $REQ_ID: Requirement ID like REQ-001 (optional, for traceability in commit messages)
- $NANO_SPEC_PATH: Path to the nano-spec task directory to commit (optional)

## Actions

### create

Create a branch, push it, create a draft PR, and optionally commit nano-spec files.

**Usage**: `branch-pr create`

**Steps:**

1. Construct the branch name: `dev-loop/<issue-number>-<feature-slug>`.
2. Create and checkout the branch:
   ```bash
   git checkout -b dev-loop/$ISSUE_NUMBER-$FEATURE_SLUG
   ```
3. Push the branch:
   ```bash
   git push -u origin dev-loop/$ISSUE_NUMBER-$FEATURE_SLUG
   ```
   Add `--repo $REPO` to `gh` commands if $REPO is provided.
4. Create a draft PR linking to the issue:
   ```bash
   gh pr create --draft --title "$ISSUE_TITLE" --body "Closes #$ISSUE_NUMBER

   Automated implementation by dev-loop agent."
   ```
5. If $NANO_SPEC_PATH is provided, commit those files:
   ```bash
   git add $NANO_SPEC_PATH
   git commit -m "docs: add nano-spec plan for #$ISSUE_NUMBER [REQ-XXX]"
   ```
   Include `[REQ-XXX]` only if $REQ_ID is available.
6. Push the commit.
7. Return the PR number and URL for use by subsequent steps.

### Output Format (create)
```
Branch: dev-loop/<issue-number>-<feature-slug>
PR: #<pr-number> (<pr-url>)
Commit: <sha> (nano-spec files, if committed)
```

---

### push

Push the current branch to its remote tracking branch.

**Usage**: `branch-pr push`

**Steps:**

1. Push the current branch:
   ```bash
   git push
   ```
2. If no upstream is set, push with `-u origin <current-branch>`.

### Output Format (push)
```
Pushed: <branch-name> -> origin/<branch-name>
```
