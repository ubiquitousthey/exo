---
name: req-decompose
description: Decompose a product-phase directory (requirements.md + architecture.md) into GitHub issues, one per requirement. Supports "scan", "create", and "status".
---

# req-decompose: Requirements to GitHub Issues

Processes a product-phase directory and creates richly-expanded GitHub issues from `requirements.md`, using `architecture.md` as technical context. Each requirement becomes one issue with background, goals, acceptance criteria, technical context, dependencies, and open questions — structured so the dev-loop agent can pick them up directly.

## Arguments
- $ACTION: The action to perform (scan, create, status)
- $PHASE_DIR: Path to the product-phase directory (must contain requirements.md)
- $REPO: Repository in owner/repo format (optional, defaults to current repo)

## Parsing requirements.md

Requirements are delimited by level-2 headings matching the pattern `## REQ-XXX: Title`. Each requirement block runs from its heading to the next `## REQ-` heading or end of file.

Each requirement block may contain a `<!-- req-meta ... -->` HTML comment with structured metadata:

```html
<!-- req-meta
Type: feature
Priority: must-have
Dependencies: [REQ-001, REQ-003]
-->
```

Parse this comment block as simple `Key: Value` lines:
- **Type**: `feature | bug | chore | spike` (default: `feature`)
- **Priority**: `must-have | should-have | could-have | wont-have` (default: `must-have`)
- **Dependencies**: bracketed comma-separated list of REQ IDs, or `[]` for none (default: `[]`)

Everything outside the `<!-- req-meta -->` comment is the requirement's prose description.

The document-level heading (`# Requirements — ...`) and any content before the first `## REQ-` heading is the **phase preamble** — use it as shared context (phase name, goal) when expanding each requirement.

## Issue Body Template

For each requirement, generate a GitHub issue body using this structure:

```markdown
## Background
{Why this requirement exists. Synthesize from the requirement's prose and the phase
preamble (phase goal, context). 2-4 sentences.}

## Goals
- {What success looks like — specific, measurable outcomes}
- {One bullet per distinct goal}

## Acceptance Criteria
- [ ] {Specific, testable condition derived from the requirement description}
- [ ] {Each criterion maps to one verifiable behavior}
- [ ] {Include edge cases and error conditions where implied by the requirement}

## Technical Context
{Relevant information from architecture.md. Identify which components, data models,
or integrations are involved in this requirement. Quote or paraphrase architecture.md
sections — do not invent architecture that is not documented.}

{If architecture.md is missing or has no relevant sections, write:
"No architecture document provided. Implementation should follow existing project patterns."}

## Implementation Hints
{Optional. Inferred approach based on architecture.md patterns, component boundaries,
or technology choices documented there. Omit this section entirely if architecture.md
provides no relevant guidance.}

## Dependencies
{For each declared dependency, write: "Blocked by #N — REQ-XXX: Title"
once issue numbers are known (filled in during create's second pass).
Write "None" if no dependencies declared.}

## Open Questions
{List questions a human must answer before this requirement can be implemented.
Apply the detection criteria below. Each question should be specific and actionable.
Omit this section entirely if there are no open questions.}

- [ ] {Specific question with enough context to answer it}

---
<!-- req-decompose
source_req: REQ-XXX
phase_dir: {$PHASE_DIR}
-->
```

## Open Question Detection Criteria

Surface an open question when any of these conditions are met:

1. **Missing integration contract** — the requirement references an external system, API, or service without specifying authentication, data format, error handling, or endpoint details.
2. **Vague quantifiers** — the requirement uses imprecise terms without measurable definitions: "fast", "scalable", "many", "reasonable", "large", "soon", "performant".
3. **Unresolved architecture decision** — an item in architecture.md's `Open Architecture Decisions` section is relevant to this requirement.
4. **Requirement conflict** — this requirement conflicts with or overlaps another requirement in the same phase in a way that requires a human decision to resolve.
5. **Ambiguous dependency** — a declared dependency's own requirement description is vague enough that this requirement's implementation could go multiple ways depending on how the dependency is resolved.
6. **Missing actor or trigger** — the requirement describes behavior without specifying who or what initiates it.
7. **Undefined error handling** — the requirement describes a happy path without specifying what happens on failure.

## Actions

### scan

Preview issues that would be created. Makes no GitHub API calls and writes no files.

**Usage**: `/req-decompose scan path/to/phase-dir [--repo owner/repo]`

1. Verify `$PHASE_DIR/requirements.md` exists. If not, error: "requirements.md not found in $PHASE_DIR" and stop.
2. Read `$PHASE_DIR/architecture.md` if it exists. If missing, warn: "architecture.md not found — Technical Context sections will be limited."
3. Read any other `.md` files in `$PHASE_DIR` as supplementary context (but do not parse them for requirements).
4. Parse `requirements.md` per the parsing rules above. Extract all `## REQ-XXX:` blocks.
5. For each requirement:
   a. Generate the full issue body per the Issue Body Template.
   b. Apply Open Question Detection Criteria — list each detected question.
   c. Determine label eligibility:
      - All requirements get `needs-refinement`.
      - Requirements with **zero open questions AND no declared dependencies** also get `claude-ready`.
      - Requirements with declared dependencies also get `blocked`.
6. Print the preview.

### Output Format (scan)
```
Scan results for: $PHASE_DIR
Requirements found: N
architecture.md: found | not found

---

REQ-001: User Authentication
  Priority: must-have | Type: feature
  Dependencies: none
  Open questions: 2
  Labels: needs-refinement
  ---
  [full issue body preview]

---

REQ-002: Password Reset
  Priority: should-have | Type: feature
  Dependencies: REQ-001
  Open questions: 0
  Labels: needs-refinement, blocked

---

REQ-003: Audit Logging
  Priority: should-have | Type: feature
  Dependencies: none
  Open questions: 0
  Labels: needs-refinement, claude-ready

---

Summary:
  N issues would be created
  M with open questions (need human review before claude-ready)
  K eligible for auto claude-ready
  J with dependencies (will be labeled blocked)
```

---

### create

Create GitHub issues and write the phase manifest.

**Usage**: `/req-decompose create path/to/phase-dir [--repo owner/repo]`

1. Check for `$PHASE_DIR/manifest.json`. If it exists, stop and warn:
   ```
   manifest.json already exists at $PHASE_DIR/manifest.json
   Run `/req-decompose status $PHASE_DIR` to check existing issues.
   Delete manifest.json to re-create (this will create duplicate issues).
   ```
2. Run the same parse and expansion logic as `scan` (steps 1–5).

3. **First pass — create all issues.** For each requirement in document order:
   ```bash
   gh issue create \
     --title "REQ-XXX: Title" \
     --body "$(cat <<'ISSUE_BODY'
   [full expanded issue body with Dependencies section saying "Pending — will be linked after all issues are created"]
   ISSUE_BODY
   )" \
     --label "needs-refinement" [--repo $REPO]
   ```
   Capture the issue number from the returned URL (the trailing number in the `https://github.com/.../issues/N` output).
   Build a map: REQ-ID → issue number.

4. **Second pass — patch dependency links.** For each requirement with declared dependencies:
   a. Resolve each dependency REQ-ID to its issue number from the map.
   b. Replace the Dependencies section placeholder with real `Blocked by #N — REQ-XXX: Title` links.
   c. Edit the issue body:
      ```bash
      gh issue edit N --body "$(cat <<'ISSUE_BODY'
      [updated body with resolved dependency links]
      ISSUE_BODY
      )" [--repo $REPO]
      ```
   d. Add the `blocked` label:
      ```bash
      gh issue edit N --add-label "blocked" [--repo $REPO]
      ```

5. **Third pass — auto claude-ready.** For each requirement with zero open questions AND no declared dependencies:
   ```bash
   gh issue edit N --add-label "claude-ready" [--repo $REPO]
   ```

6. Write `$PHASE_DIR/manifest.json`:
   ```json
   {
     "phase": "<basename of $PHASE_DIR>",
     "repo": "<owner/repo or null if using current repo>",
     "created_at": "YYYY-MM-DD",
     "requirements": {
       "REQ-001": {
         "issue": 42,
         "title": "User Authentication",
         "nano_spec": null,
         "bdd_feature": null,
         "pr": null
       },
       "REQ-002": {
         "issue": 43,
         "title": "Password Reset",
         "nano_spec": null,
         "bdd_feature": null,
         "pr": null
       }
     }
   }
   ```
   The `nano_spec`, `bdd_feature`, and `pr` fields start as `null`. They are populated later by the dev-loop agent (or by `req-decompose status` when it discovers them) to complete the traceability chain.

### Output Format (create)
```
Created issues for: $PHASE_DIR

REQ-001: User Authentication → #42 [needs-refinement]
REQ-002: Password Reset → #43 [needs-refinement, blocked] (blocked by #42)
REQ-003: Audit Logging → #44 [needs-refinement, claude-ready]

Summary:
  N issues created
  K auto-labeled claude-ready (zero open questions, no dependencies)
  M need human review before claude-ready
  J labeled blocked (have dependencies)
  Manifest written: $PHASE_DIR/manifest.json
```

---

### status

Check current state of previously created issues for this phase.

**Usage**: `/req-decompose status path/to/phase-dir [--repo owner/repo]`

1. Look for `$PHASE_DIR/manifest.json`. If missing, error:
   ```
   No manifest found at $PHASE_DIR/manifest.json
   Run `/req-decompose create $PHASE_DIR` first.
   ```
2. Read the manifest. Determine `--repo` from the manifest's `repo` field if not provided as an argument.
3. For each requirement entry in the manifest, fetch current issue state:
   ```bash
   gh issue view N --json number,title,state,labels,assignees [--repo $REPO]
   ```
4. **Discover downstream artifacts** for traceability. For each requirement whose `nano_spec`, `bdd_feature`, or `pr` fields are `null`:
   - Check if `tasks/dev-loop-<issue-number>/` exists locally → populate `nano_spec` path.
   - Search for `.feature` files containing `@issue-<issue-number>` tag → populate `bdd_feature` path.
   - Check for a PR linked to the issue:
     ```bash
     gh pr list --search "<issue-number>" --state all --json number,headBranch --jq '.[0]' [--repo $REPO]
     ```
     → populate `pr` number.
   - Update `manifest.json` with any newly discovered values.
5. Compute summary: open vs closed, label distribution, traceability completeness.

### Output Format (status)
```
Status for phase: <phase name>
Repo: <owner/repo>
Checked: YYYY-MM-DD

REQ-001: User Authentication → #42
  State: open | Labels: dev-loop-active | Assignee: @alice
  Nano-spec: tasks/dev-loop-42/ | BDD: tests/bdd/req-001-user-auth.feature | PR: #55

REQ-002: Password Reset → #43
  State: open | Labels: needs-refinement, blocked
  Nano-spec: — | BDD: — | PR: —

REQ-003: Audit Logging → #44
  State: closed | Labels: dev-loop-review
  Nano-spec: tasks/dev-loop-44/ | BDD: tests/bdd/req-003-audit-logging.feature | PR: #57

Summary:
  N total | C closed | O open
  Pipeline: X needs-refinement → Y claude-ready → Z dev-loop-active → W dev-loop-review
  Traceability: T/N requirements have full chain (issue → nano-spec → BDD → PR)
```
