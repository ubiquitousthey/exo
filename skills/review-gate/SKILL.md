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
- $BDD_FEATURE_PATH: Path to the BDD feature file
- $FEATURE_SLUG: The feature slug (for resume instructions)
- $DESIGN_PATHS: Comma-separated list of design file paths (optional)
- $REPO: Repository in owner/repo format (optional)

## Actions

### post

Post the plan and BDD spec as a PR comment for human review.

**Usage**: `review-gate post`

**Steps:**

1. Read the nano-spec files:
   - `$NANO_SPEC_PATH/README.md` for background, goals, scope
   - `$NANO_SPEC_PATH/todo.md` for implementation phases
   - `$NANO_SPEC_PATH/doc.md` for open questions
2. Read the BDD feature file at $BDD_FEATURE_PATH.
3. If $DESIGN_PATHS is provided, gather design file descriptions from the nano-spec UI Design section.
4. Build and post the review comment:
   ```bash
   gh pr comment $PR_NUMBER --body "$(cat <<'EOF'
   ## Review Gate — Plan & BDD Spec

   ### Nano-spec Plan
   <README.md contents>

   ### Implementation Phases
   <todo.md contents>

   ### BDD Feature Spec
   ```gherkin
   <feature file contents>
   ```

   ### UI Designs
   <If designs exist, list design file paths and descriptions. If none, omit this section.>

   ### Open Questions
   <open questions from doc.md, or "None">

   ---
   **Please review the plan and BDD spec above.**
   - Reply with feedback to request changes.
   - Comment `lgtm` to approve.

   Then resume implementation with:
   ```
   /dev-loop --resume <feature-slug>
   ```
   EOF
   )"
   ```
   Add `--repo $REPO` if provided.
5. Add the `dev-loop-review-gate` label:
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
2. Find the review gate comment (contains "Review Gate — Plan & BDD Spec").
3. Examine all comments posted after the review gate:
   - If an `lgtm` comment is found → report `approved: true`.
   - If other feedback comments exist → report `approved: false` with the feedback content.
   - If no comments after the review gate → report `approved: pending`.
4. If approved, remove the `dev-loop-review-gate` label:
   ```bash
   gh pr edit $PR_NUMBER --remove-label dev-loop-review-gate
   ```

### Output Format (check)
```
Status: approved | feedback | pending
Feedback: <summary of feedback comments, if any>
Label removed: yes | no
```
