---
name: issue-pick
description: Find, claim, and complete GitHub issues labeled for automated development. Supports "pick an issue", "claim issue 42", "complete issue 42".
---

# issue-pick: GitHub Issue Selection

Manage GitHub issues through the dev-loop lifecycle using `gh` CLI.

## Arguments
- $ACTION: The action to perform (pick, claim, complete)
- $ISSUE_NUMBER: The issue number (required for claim and complete, ignored for pick)
- $REPO: Repository in owner/repo format (optional, defaults to current repo)

## Actions

### pick
Find the oldest open issue labeled `claude-ready`.

**Usage**: `/issue-pick pick [--repo owner/repo]`

1. Run:
   ```bash
   gh issue list --label claude-ready --state open --limit 1 --json number,title,body,labels,assignees --jq '.[0]'
   ```
   Add `--repo $REPO` if provided.
2. If the result is empty or null, report: "No issues with `claude-ready` label found." and stop.
3. Return the issue's number, title, body, and labels.

### Output Format (pick)
```
Found issue #<number>: <title>

Labels: <comma-separated labels>

<body>
```

---

### claim
Claim an issue for dev-loop processing.

**Usage**: `/issue-pick claim <number> [--repo owner/repo]`

1. Add the `dev-loop-active` label:
   ```bash
   gh issue edit $ISSUE_NUMBER --add-label dev-loop-active
   ```
2. Remove the `claude-ready` label:
   ```bash
   gh issue edit $ISSUE_NUMBER --remove-label claude-ready
   ```
3. Assign to the current user:
   ```bash
   gh issue edit $ISSUE_NUMBER --add-assignee @me
   ```
   Add `--repo $REPO` to each command if provided.

### Output Format (claim)
```
Claimed issue #<number>:
- Added label: dev-loop-active
- Removed label: claude-ready
- Assigned to: @me
```

---

### complete
Mark an issue as completed by dev-loop, ready for human review.

**Usage**: `/issue-pick complete <number> [--repo owner/repo]`

1. Remove `dev-loop-active` label:
   ```bash
   gh issue edit $ISSUE_NUMBER --remove-label dev-loop-active
   ```
2. Add `dev-loop-review` label:
   ```bash
   gh issue edit $ISSUE_NUMBER --add-label dev-loop-review
   ```
   Add `--repo $REPO` to each command if provided.

### Output Format (complete)
```
Completed issue #<number>:
- Removed label: dev-loop-active
- Added label: dev-loop-review
- Ready for human review
```
