---
name: interview
description: Identify the top 5 most important decisions for an issue and capture human answers via the Review Gate. Use "interview formulate" to produce structured questions, or "interview parse" to extract answers from the user's reply.
---

# interview: Top-5 Decisions Interview

Before implementation begins, force the agent to surface the decisions it's about to make on autopilot. Pick the 5 highest-impact ones and put them in front of the human at the Review Gate. Cheap to ask now; expensive to fix later.

## Arguments
- $ACTION: The action to perform (formulate, parse)
- $NANO_SPEC_PATH: Path to the nano-spec task directory (required)
- $ISSUE_NUMBER: The GitHub issue number (required for parse)
- $REPLY_TEXT: The user's reply text from the PR comment (required for parse)
- $REPO: Repository in owner/repo format (optional)

## Concept

Three sources feed the decision pool:

1. **Explicit open questions.** From the realigned issue body's `Open Questions` section (if present) and `nano-spec doc.md`'s `Open Questions` section.
2. **Recorded decisions.** From `nano-spec doc.md`'s `Key Decisions` section. The agent already chose A over B; surface the choice and ask the human to confirm.
3. **Implicit assumptions.** Decisions the agent made silently while planning. These are usually invisible until they bite. Find them by reading the plan and asking: "what could a reasonable person have decided differently here?"

Pool everything, score, pick top 5.

## Scoring

For each candidate decision, sum these weights:

| Trait | Weight |
|-------|--------|
| Would change the AC list or BDD scenarios if decided differently | +3 |
| Irreversible or expensive to undo (data migration, public API shape, schema change) | +3 |
| Touches code owned by another team or external consumer | +2 |
| Already flagged as an open question in the issue body | +2 |
| Already flagged as an open question in `doc.md` | +2 |
| Implicit agent assumption with no explicit justification in `doc.md` | +1 |
| Stylistic / naming / minor file-organization choice | -2 |

Drop decisions with a final score below 2. Sort the rest descending. Take the top 5.

## Actions

### formulate

Identify the top 5 decisions and produce a structured Markdown question block.

**Usage**: `interview formulate`

**Steps:**

1. Read `$NANO_SPEC_PATH/README.md`, `$NANO_SPEC_PATH/todo.md`, and `$NANO_SPEC_PATH/doc.md` (if present).
2. Read the parent issue body (the realigned version). Pull the `Open Questions` section if present.
3. Build the candidate decision pool from all three sources above.
4. Score each candidate. Drop low scorers. Sort by score.
5. Take the top 5 (or fewer if there are fewer than 5 above the threshold).
6. For each, write a question with:
   - A short identifier `Q1` … `Q5`
   - A one-sentence question phrased so the answer is concrete (not yes/no when a tradeoff exists)
   - The agent's **current answer / assumption** so the user can accept or override
   - 2–4 plausible alternatives where relevant
   - A `scope_changing: yes | no` tag (used by `parse` to decide if the BDD spec needs rewriting)
7. Emit the question block in this exact format:

```markdown
## Top 5 Decisions

If you're happy with the agent's current answer for a question, leave it as-is or reply with `accept`. Otherwise reply with the decision you want.

### Q1 — <one-sentence question>
- **Default answer:** <agent's current assumption>
- **Alternatives:** <option B>, <option C>
- **Why it matters:** <one-line impact>
- **Scope-changing:** yes | no

### Q2 — <one-sentence question>
- **Default answer:** ...
- **Alternatives:** ...
- **Why it matters:** ...
- **Scope-changing:** yes | no

<...continue Q3, Q4, Q5...>

---

**To respond, reply on this PR with one block per question:**
```
Q1: <your answer or "accept">
Q2: <your answer or "accept">
...
```

Or comment `lgtm` to accept all defaults and proceed.
```

8. Append a small machine-readable footer for `parse` to consume:

```markdown
<!-- interview-meta
Q1: scope_changing=yes|no
Q2: scope_changing=yes|no
...
-->
```

9. Write the full question block to `$NANO_SPEC_PATH/interview.md` so it's persisted alongside the spec.
10. Return the question block as a string. The `review-gate post` action embeds it in the PR comment.

### Output Format (formulate)
```
Decisions identified: <N> (top 5 selected)
Scope-changing decisions: <count>
Interview block path: $NANO_SPEC_PATH/interview.md
```

If the candidate pool has fewer than 2 decisions above the score threshold, return an empty question block and report:
```
Decisions identified: <N> (none above threshold — interview skipped)
```

The dev-loop agent treats an empty block as "no interview needed; review-gate posts the plan as usual."

---

### parse

Read the user's reply on the PR, extract per-question answers, and update `doc.md`.

**Usage**: `interview parse`

**Steps:**

1. Read `$NANO_SPEC_PATH/interview.md` to recover the question definitions and the `<!-- interview-meta -->` footer.
2. Parse $REPLY_TEXT looking for `Q1:`, `Q2:`, ... lines. For each match, capture the answer. Treat `accept` (case-insensitive) as "use the default answer".
3. Treat a bare `lgtm` as "accept all defaults".
4. For any unanswered question, default to the agent's stated assumption and note it in the answers as `(no reply — using default)`.
5. Update `$NANO_SPEC_PATH/doc.md`:
   - If `doc.md` doesn't exist, create it with the medium template (the interview answers warrant `doc.md` even if the plan is `lite`).
   - Append or merge into a `## Decisions` section with one `### Q<N> — <question>` heading per answered decision and the final answer.
   - Move the originating items in the `## Open Questions` section to checked `[x]` once answered.
6. Compute `scope_changed`:
   - `true` if any answered question was tagged `scope_changing=yes` AND the user's answer differed from the default.
   - `false` otherwise.
7. Append a brief comment to the PR confirming what was captured:
   ```bash
   gh pr comment $PR_NUMBER --body "$(cat <<'EOF'
   ## Interview answers captured

   <table of Q<N>: final answer>

   Scope changed: <true | false>
   EOF
   )"
   ```
8. Return the parsed answers and the `scope_changed` flag.

### Output Format (parse)
```
Answers captured: <N>/<N> questions
Scope changed: true | false
doc.md updated: yes
```

If `scope_changed=true`, the dev-loop agent must rewrite the BDD feature file (and re-run the BDD guard) before resuming implementation.
