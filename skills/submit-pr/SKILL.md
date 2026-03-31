---
name: submit-pr
description: Finalize a pull request with a comprehensive description and mark it ready for review. Use "submit-pr submit" to update the PR body, mark ready, and update issue labels.
---

# submit-pr: PR Submission

Finalize a pull request with a comprehensive description including traceability, test results, and proof links, then mark it ready for human review.

## Arguments
- $ACTION: The action to perform (submit)
- $PR_NUMBER: The pull request number
- $ISSUE_NUMBER: The GitHub issue number
- $FEATURE_SLUG: The feature slug
- $NANO_SPEC_PATH: Path to the nano-spec task directory
- $BDD_FEATURE_PATH: Path to the BDD feature file
- $PROOF_PATH: Path to the proof document (optional)
- $SELF_REVIEW_SUMMARY: Summary of self-review findings and actions taken (optional)
- $BDD_RESULT: BDD test result — pass or fail (optional)
- $SUITE_RESULT: Full test suite result — pass or fail (optional)
- $FIDELITY_RATING: UI fidelity rating — High, Medium, Low (optional)
- $FIDELITY_REPORT_PATH: Path to fidelity report (optional)
- $REQ_ID: Requirement ID like REQ-001 (optional)
- $PHASE_DIR: Phase directory path from req-decompose (optional)
- $REPO: Repository in owner/repo format (optional)

## Actions

### submit

Update the PR description and mark it ready for review.

**Usage**: `submit-pr submit`

**Steps:**

1. Read the BDD feature file at $BDD_FEATURE_PATH to extract scenario names and `@AC-N` tags.
2. Update the PR description:
   ```bash
   gh pr edit $PR_NUMBER --body "$(cat <<'EOF'
   Closes #<issue-number>

   ## Traceability
   - **Requirement**: REQ-XXX (if $REQ_ID available, otherwise omit)
   - **Issue**: #<issue-number>
   - **Phase**: <phase directory> (if $PHASE_DIR available, otherwise omit)
   - **Nano-spec**: `<nano-spec-path>/`
   - **BDD Feature**: `<bdd-feature-path>`
   - **Proof**: `<proof-path>` (if $PROOF_PATH available, otherwise omit)

   ## Summary
   <bullet points of what was implemented — read from nano-spec log.md>

   ## BDD Scenarios
   <list of scenarios from the feature file, with @AC-N tags>

   ## Test Results
   - BDD tests: <$BDD_RESULT or "not run">
   - Full suite: <$SUITE_RESULT or "not run">

   ## UI Fidelity
   <If $FIDELITY_RATING provided: rating, path to fidelity report. Otherwise omit section.>

   ## Proof
   - Proof document: `<proof-path>`
   - Re-verify with: `showboat verify <proof-path>`
   <Omit section if no $PROOF_PATH>

   ## Self-Review
   <$SELF_REVIEW_SUMMARY or omit section>

   ---
   Automated implementation by dev-loop agent.
   EOF
   )"
   ```
   Add `--repo $REPO` if provided.
3. Mark the PR as ready:
   ```bash
   gh pr ready $PR_NUMBER
   ```
4. Invoke the `issue-pick` skill with action `complete $ISSUE_NUMBER` to update labels (remove `dev-loop-active`, add `dev-loop-review`).
5. Report the final status with a link to the PR.

### Output Format (submit)
```
PR #<number> submitted for review: <pr-url>
Labels updated: dev-loop-active -> dev-loop-review
Issue #<number> marked for review
```
