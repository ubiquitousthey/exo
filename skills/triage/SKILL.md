---
name: triage
description: Classify an issue into a development track (feature, bug, refactor, chore, spike) and emit flags that gate downstream dev-loop steps. Use "triage classify" to classify the realigned issue body.
---

# triage: Issue Triage

Classifies an issue and emits a flag set that gates which dev-loop steps run. Saves time by skipping BDD spec authoring on a one-line typo fix and skipping proof generation on a refactor; adds a bug-reproduction step on actual bugs.

## Arguments
- $ACTION: The action to perform (classify)
- $ISSUE_NUMBER: The GitHub issue number (required)
- $ISSUE_TITLE: The issue title (required)
- $ISSUE_BODY: The realigned issue body (required — pass the body AFTER `realign realign` has run)

## Tracks

| Track | When | Default flags |
|-------|------|---------------|
| `feature` | New user-observable behavior, new endpoint, new screen, new command | `plan_depth=full needs_bdd=true needs_repro=false needs_proof=true` |
| `bug` | Existing behavior is broken; user reports unexpected output | `plan_depth=lite needs_bdd=false needs_repro=true needs_proof=false` |
| `refactor` | Internal restructuring, no behavior change. Existing tests must still pass. | `plan_depth=lite needs_bdd=false needs_repro=false needs_proof=false` |
| `chore` | Doc-only change, dep bump, config tweak, lint fix | `plan_depth=lite needs_bdd=false needs_repro=false needs_proof=false` |
| `spike` | Investigation, POC, research with a writeup as deliverable | `plan_depth=lite needs_bdd=false needs_repro=false needs_proof=true` |

`needs_ui` is not a triage flag — the `ui-design` skill auto-detects UI work from the issue body. Triage does not override it.

## Classification

Always infer from issue content. Do not trust pre-existing `<!-- req-meta Type: ... -->` metadata — it may be stale or wrong relative to the realigned body.

### Detection rules

Run all rules. Score the issue against each track and pick the highest scorer. Tie-break in this priority order: `bug > spike > refactor > chore > feature`.

**Bug indicators** (any match: +2 each, max +6):
- Body contains "steps to reproduce", "expected", "actual", "expected vs actual", "what happened", "what should happen"
- Stack trace, error message, or exception name in the body
- Words: "broken", "fails", "crash", "regression", "doesn't work", "incorrect output", "wrong"
- `bug` label or `[bug]` in title
- A previous working state is referenced ("worked in v1.2", "since the upgrade")

**Refactor indicators** (any match: +2 each, max +6):
- Words: "refactor", "extract", "rename", "consolidate", "DRY", "deduplicate", "split", "merge module", "internal cleanup"
- Body explicitly states "no behavior change" or equivalent
- `refactor` or `tech-debt` label
- Body lists implementation moves with no user-observable outcome

**Chore indicators** (any match: +2 each, max +6):
- Pure documentation change (only `*.md`, `docs/`, comments)
- Dependency bump (only manifest files like `package.json`, `pyproject.toml`, `Gemfile`, `Cargo.toml`)
- Config tweak (only `*.json`, `*.yaml`, `*.toml`, `.env*` config files)
- Lint or formatter setting change
- `chore`, `docs`, or `deps` label

**Spike indicators** (any match: +2 each, max +6):
- Words: "investigate", "spike", "research", "explore", "POC", "proof of concept", "feasibility"
- Body asks "can we ..." or "should we ..." style questions
- Outcome is a writeup, decision document, or recommendation rather than shipped behavior
- `spike`, `research`, or `investigate` label

**Feature indicators** (any match: +1 each, max +4):
- New user-observable behavior described
- "Add ", "implement ", "support ", "enable " phrasing in the title
- AC list describes outcomes a user can see
- `feature` or `enhancement` label
- Anything not matching the other tracks falls back to feature with confidence `low`

### Confidence

- `high` — winning score is at least 4 AND at least 2 points clear of the runner-up
- `medium` — winning score is at least 2 AND at least 1 point clear
- `low` — anything else (default to `feature` track)

If confidence is `low`, surface the ambiguity in the report and recommend the dev-loop agent confirm with the user before proceeding.

## Action

### classify

**Usage**: `triage classify`

**Steps:**

1. Read $ISSUE_BODY. If the body has been through `realign realign`, parse the rewritten structure (`## Core Need`, `## Acceptance Criteria`, `## Current-System Context`). Otherwise read the body verbatim.
2. Run all four detection rule sets (bug, refactor, chore, spike). Compute scores. Apply the feature fallback.
3. Determine the winning track and confidence per the rules above.
4. Apply the default flags for the chosen track from the table.
5. Apply flag overrides for edge cases:
   - If track is `bug` BUT the body explicitly asks for a new BDD scenario or describes a multi-step user flow, set `needs_bdd=true` (a bug fix that warrants user-facing behavior verification).
   - If track is `chore` BUT the diff will touch source code beyond config/docs, upgrade `plan_depth=full` (the agent must inspect what it's touching).
   - If track is `feature` BUT the issue is a single-line behavior tweak with one obvious AC, downgrade `plan_depth=lite`.
6. Return the structured report.

### Output Format (classify)
```
Triage: <track> (confidence: high | medium | low)
Reasoning: <one paragraph citing the strongest 2-3 indicators>

Flags:
  plan_depth: full | lite
  needs_bdd: true | false
  needs_repro: true | false
  needs_proof: true | false

Recommendation:
  - <step in the dev-loop and whether it should run, e.g., "Step 5 BDD spec: SKIP (refactor track)">
```

If confidence is `low`, append:
```
Confidence is LOW. The dev-loop agent should pause and confirm the track with the user before proceeding.
```
