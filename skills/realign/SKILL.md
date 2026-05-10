---
name: realign
description: Align a GitHub issue with the current state of the system before planning. Detects drift in references (file paths, components, endpoints), isolates the user-need, and rewrites the issue body. Use "realign realign" to update the issue, or "realign check" for a read-only drift report.
---

# realign: Align Issue With Current System

By the time `/dev-loop` picks up an issue, references in the issue body may be stale: files renamed, components replaced, decisions superseded, behavior already implemented. This skill isolates the user-need, verifies every concrete reference against the current code, and rewrites the issue body so downstream steps consume a current-system brief.

## Arguments
- $ACTION: The action to perform (realign, check)
- $ISSUE_NUMBER: The GitHub issue number (required)
- $REQ_ID: Requirement ID like REQ-001 (optional, preserved in metadata)
- $REPO: Repository in owner/repo format (optional, defaults to current repo)

## Core Concept

An issue is two things bundled together:
1. **The user-need** — who wants what observable outcome.
2. **Implementation hints** — references to files, components, endpoints, schemas, libraries that the issue's author thought were the right place to make the change.

The user-need is durable. Implementation hints rot.

This skill separates the two, verifies the hints against the current system, and rewrites the issue so the user-need is preserved while the hints are reimagined in light of what the code looks like today.

## Actions

### realign

Edit the issue body in place and post a comment summarizing the changes.

**Usage**: `realign realign`

**Steps:**

#### 1. Fetch the current issue
```bash
gh issue view $ISSUE_NUMBER --json number,title,body,labels [--repo $REPO]
```
If the body already contains a `<!-- realigned: YYYY-MM-DD ... -->` marker dated within the last 7 days, skip and report "Already realigned recently — use `realign check` to inspect."

#### 2. Extract the user-need

Read the issue body. Identify the *actor* (user, operator, calling service, scheduled job, downstream consumer, developer) and the *observable outcome* they want. Write a one-paragraph "Core Need" statement of the form:

> When `<actor>` `<does something>`, `<observable outcome>`.

Strip implementation language. If the issue body is purely implementation-shaped (e.g., "refactor X to use Y") and you cannot derive an actor + outcome, set `needs_human=true` and stop with a report asking the human to add the user-need.

#### 3. Inventory references

Pull every concrete reference from the issue body:

- File paths (e.g., `src/auth/middleware.py`)
- Function or class names (e.g., `AuthMiddleware`, `reset_password`)
- Component or module names (e.g., `BillingService`, `<UserCard>`)
- Library names (e.g., `passport`, `fastapi`)
- Endpoint paths (e.g., `/v1/users`, `POST /reset-password`)
- Environment variables (e.g., `DATABASE_URL`)
- Table or column names (e.g., `users.is_active`)
- Configuration keys (e.g., `auth.session_ttl`)

Build a checklist. Order them by specificity (paths first, then symbols, then schema).

#### 4. Verify each reference against current code

For each reference, search the codebase to confirm it exists and means what the issue assumes:

- File paths → `ls` / `Read` to confirm existence.
- Symbols → `grep -r "<name>"` to confirm definition still exists in the same role.
- Endpoints → grep route definitions.
- Tables/columns → grep migrations or ORM models.
- Libraries → check the project manifest (`pyproject.toml`, `package.json`, etc.).

Mark each as one of:

- `current` — reference still exists and serves the same role.
- `renamed → <new>` — exists under a different name; cite the new name.
- `removed` — no longer exists.
- `superseded by <thing>` — replaced by a different abstraction or pattern.

Use the most efficient search method. For broader exploration, dispatch the `Explore` agent with a focused query (e.g., "where is `AuthMiddleware` now and what replaced it?"). Don't search blindly — work the checklist.

#### 5. Reimagine the implementation hints

For every reference marked anything other than `current`, restate the original intent in terms of what's there now. Produce a "Current-System Context" block: a short prose paragraph plus a bullet list mapping old → new for each drifted reference.

If the user-need itself is now obsolete (e.g., the behavior the issue asks for has already been implemented elsewhere), set `needs_human=true` and stop. Report the evidence.

#### 6. Rewrite the issue body

Build the new body using this template:

```markdown
## Core Need
<actor + observable outcome from step 2>

## Acceptance Criteria
<preserved verbatim from the original — they will be re-checked against the
user-perspective rule by downstream skills>

## Current-System Context
<reimagined implementation hints from step 5>

**Reference drift:**
- `<old reference>` → <status: renamed/removed/superseded — pointer to current>
- `<old reference>` → <status>

## Original Issue (preserved)

<details>
<summary>Click to expand the original issue body</summary>

<verbatim copy of the original body>

</details>

---
<!-- realigned: YYYY-MM-DD source_req: REQ-XXX -->
<!-- realign-by: dev-loop -->
```

If a `<!-- req-decompose ... -->` footer was present in the original, preserve it verbatim above the realign footer.

Apply the edit:
```bash
gh issue edit $ISSUE_NUMBER --body "$(cat <<'BODY'
<rewritten body>
BODY
)" [--repo $REPO]
```

#### 7. Post a summary comment

```bash
gh issue comment $ISSUE_NUMBER --body "$(cat <<'COMMENT'
## Realignment (YYYY-MM-DD)

**Drift detected:**
- `<reference>` → <status>
- `<reference>` → <status>

**Core need (unchanged | clarified | rescoped):** <one-sentence summary>

**What changed in the issue body:**
- Added "Core Need" section isolating the user-observable outcome.
- Added "Current-System Context" with reference drift mapping.
- Preserved the original body in a collapsed `<details>` block.

The Acceptance Criteria list was preserved verbatim. Downstream steps will
re-check each AC against the user-perspective rule and may rewrite or flag
implementation-shaped criteria.
COMMENT
)" [--repo $REPO]
```

If no drift was detected (everything `current`), still post a comment but say "No drift detected — issue references all match the current system." Skip the body rewrite in that case but still write the `<!-- realigned: ... -->` marker so a future re-run knows it was checked.

#### 8. Return structured output

```
Realignment: PASS | NEEDS_HUMAN
Issue: #<number>
Core need: <one-sentence summary>
References checked: <count>
Drift:
  - <reference>: <status>
Body updated: yes | no (no drift)
Comment posted: <comment URL>
needs_human: true | false
```

If `needs_human=true`, the dev-loop agent must pause and surface the report to the user.

---

### check

Read-only variant. Run steps 1–5 and report without editing the issue or posting a comment.

**Usage**: `realign check`

Useful for `--review-plan` mode, for periodic drift audits on long-lived issues, and for the resume flow when an issue may have been edited since the last realignment.

### Output Format (check)
```
Realignment Check: <issue> #<number>
Core need: <one-sentence summary>
References checked: <count>
Drift:
  - <reference>: <status>
Recommendation: realign | no-op | needs_human
```

Recommendation logic:
- `realign` if any reference drifted.
- `no-op` if all references are `current` and the existing body already has a `## Core Need` section.
- `needs_human` if the user-need itself is obsolete or cannot be derived from the body.
