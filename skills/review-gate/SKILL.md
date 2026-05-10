---
name: review-gate
description: Post a plan and BDD spec as a PR comment for human review, then manage feedback. Use "review-gate post" to create the review gate, or "review-gate check" to read feedback.
---

# review-gate: PR Review Gate

Post a plan summary as a PR comment for human review and manage the review feedback cycle.

## Arguments
- $ACTION: The action to perform (post, check)
- $PR_NUMBER: The pull request number
- $NANO_SPEC_PATH: Path to the nano-spec task directory
- $BDD_FEATURE_PATH: Path to the BDD feature file (optional — omit on the bug/refactor/chore track)
- $REPRO_TEST_PATH: Path to the bug reproduction test file (optional — bug track only)
- $FEATURE_SLUG: The feature slug (for resume instructions)
- $DESIGN_PATHS: Comma-separated list of design file paths (optional)
- $INTERVIEW_BLOCK: Markdown block with top-5 decisions from `interview formulate` (optional — pass as a string. Empty/omitted = no interview)
- $TRACK: Triage track label (`feature | bug | refactor | chore | spike`), used in the post header (optional)
- $REPO: Repository in owner/repo format (optional)

## Actions

### post

Post the plan and BDD spec as a PR comment for human review.

**Usage**: `review-gate post`

**Steps:**

1. Read the nano-spec files:
   - `$NANO_SPEC_PATH/README.md` for background, goals, scope
   - `$NANO_SPEC_PATH/todo.md` for implementation phases
   - `$NANO_SPEC_PATH/doc.md` for open questions (if present — `lite` plans skip `doc.md`)
2. Read the BDD feature file at $BDD_FEATURE_PATH if provided. Skip this on tracks where no BDD spec was authored.
3. Read the reproduction test at $REPRO_TEST_PATH if provided. Include it on the bug track.
4. If $DESIGN_PATHS is provided, gather design file descriptions from the nano-spec UI Design section.
5. Build and post the review comment. Include only the sections that apply to this track:
   ```bash
   gh pr comment $PR_NUMBER --body "$(cat <<'EOF'
   ## Review Gate — <Track | "Plan & BDD Spec" if no track provided>

   ### Nano-spec Plan
   <README.md contents>

   ### Implementation Phases
   <todo.md contents>

   ### BDD Feature Spec        <-- only if $BDD_FEATURE_PATH provided
   ```gherkin
   <feature file contents>
   ```

   ### Bug Reproduction Test   <-- only if $REPRO_TEST_PATH provided
   ```<lang>
   <test file contents>
   ```

   ### UI Designs
   <If designs exist, list design file paths and descriptions. If none, omit this section.>

   <$INTERVIEW_BLOCK>           <-- inserted verbatim if non-empty; otherwise omit

   ### Open Questions
   <open questions from doc.md, or "None">

   ---
   **Please review and respond.**
   - If an interview block is present, answer each `Q<N>:` line in your reply (or `accept` to take the default; `lgtm` accepts all defaults).
   - Otherwise reply with feedback to request changes, or `lgtm` to approve.

   Then resume implementation with:
   ```
   /dev-loop --resume <feature-slug>
   ```
   EOF
   )"
   ```
   Add `--repo $REPO` if provided.
6. Add the `dev-loop-review-gate` label:
   ```bash
   gh pr edit $PR_NUMBER --add-label dev-loop-review-gate
   ```

### Output Format (post)
```
Review gate posted on PR #<number>
Label added: dev-loop-review-gate
Resume with: /dev-loop --resume <feature-slug>
```

---

### check

Read PR comments to determine if feedback was left or the plan was approved.

**Usage**: `review-gate check`

**Steps:**

1. Read PR comments since the review gate post:
   ```bash
   gh pr view $PR_NUMBER --comments --json comments
   ```
   Add `--repo $REPO` if provided.
2. Find the review gate comment (contains "Review Gate —").
3. Examine all comments posted after the review gate:
   - If an `lgtm` comment is found and no Q-answers are present → report `approved: true`, `interview_reply: ""`.
   - If a comment contains lines matching `^Q\d+:` → capture the comment body verbatim as `interview_reply`. Report `approved: true` if `lgtm` is also in the body, otherwise `approved: true` (Q-answers count as approval). The dev-loop agent runs `interview parse` next.
   - If other feedback comments exist (no Q-answers, no `lgtm`) → report `approved: false` with the feedback content.
   - If no comments after the review gate → report `approved: pending`.
4. If approved, remove the `dev-loop-review-gate` label:
   ```bash
   gh pr edit $PR_NUMBER --remove-label dev-loop-review-gate
   ```

### Output Format (check)
```
Status: approved | feedback | pending
Interview reply: <verbatim body of the reply containing Q-answers, or "" if none>
Feedback: <summary of feedback comments, if any>
Label removed: yes | no
```
