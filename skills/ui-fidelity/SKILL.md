---
name: ui-fidelity
description: Verify implemented UI matches design intent through static template audit and visual screenshot comparison. Use "ui-fidelity check" for the full flow, "ui-fidelity audit-only" for just static analysis, or "ui-fidelity compare-only" for just visual comparison.
---

# ui-fidelity: UI Fidelity Verification

Verify that implemented UI matches the design intent through static template analysis and visual screenshot comparison. Orchestrates the `ui-audit` skill for static checks and rodney for visual comparison.

## Arguments
- $ACTION: The action to perform (check, audit-only, compare-only)
- $NANO_SPEC_PATH: Path to the nano-spec task directory
- $BASE_BRANCH: The base branch to diff against (default: `main`)
- $ISSUE_NUMBER: The GitHub issue number (for commit messages)
- $REQ_ID: Requirement ID like REQ-001 (optional)

## Skip Conditions

**Skip this skill entirely** if BOTH of the following are true:
- The nano-spec `$NANO_SPEC_PATH/README.md` has no UI Design section (no designs exist)
- `git diff --name-only $BASE_BRANCH...HEAD` shows no `*.html` files

If only one condition is met, run the applicable sub-steps.

## Actions

### check

Run the full fidelity flow: static template audit + visual comparison.

**Usage**: `ui-fidelity check`

**Steps:**

#### 1. Static Template Audit

1. Check if `git diff --name-only $BASE_BRANCH...HEAD` includes `*.html` files. If not, skip this sub-step.
2. Check for `.template-audit.yaml` in the project root. If absent, log a note ("No template audit config found, skipping static audit") and skip.
3. Invoke the `ui-audit` skill with action `run`.
4. If the audit passes (no errors, only warnings): log results and proceed.
5. If errors are found: fix the violations in the template code, re-run the audit. **Max 3 iterations.** After 3 iterations, log remaining violations as warnings and proceed.
6. Commit any fixes:
   ```bash
   git add <fixed-template-files>
   git commit -m "fix: address template audit violations for #$ISSUE_NUMBER"
   ```
7. Push the commit.

**If no designs exist** (no UI Design section in nano-spec): skip visual comparison, jump to Handle Results.

#### 2. Prepare Comparison Pairs

1. Read `$NANO_SPEC_PATH/README.md` UI Design section.
2. Map each design file to its corresponding implementation URL (route or page).
3. Build a list of comparison pairs: `(design HTML path, implementation URL)`.

#### 3. Capture Screenshots

For each comparison pair:
1. Use rodney to screenshot the superdesign HTML file (`file://` path to the `.superdesign/design_iterations/*.html` file).
2. Use rodney to screenshot the running implementation page at its URL.
3. Store all screenshots in `.superdesign/fidelity_check/`.

#### 4. Visual Comparison

Review both screenshots for each pair across 6 dimensions:

| Dimension | What to check |
|-----------|---------------|
| Layout structure | Overall page structure, grid/flex layout, section ordering |
| Component presence | All expected components present (buttons, inputs, cards, etc.) |
| Typography hierarchy | Heading levels, font sizes, text weight/style |
| Color/theming | Background colors, text colors, accent colors, theme consistency |
| Spacing/alignment | Margins, padding, element alignment, whitespace |
| Interactive elements | Buttons, links, form controls, navigation elements |

Rate each dimension: **Match**, **Close**, or **Divergent**.

Determine overall fidelity:
- **High** — All dimensions are Match or Close
- **Medium** — 1-2 dimensions are Divergent
- **Low** — 3+ dimensions are Divergent

#### 5. Handle Results

Combine template audit status with visual fidelity rating:

- **High fidelity + audit pass** — Log pass, proceed.
- **Medium/High fidelity + audit errors remaining** — Proceed with a warning logged.
- **Medium or Low fidelity** — Fix the implementation to better match the design, re-capture screenshots, and re-evaluate. **Max 3 iterations.**
  - After 3 iterations: **Medium** proceeds with a warning. **Low** pauses and asks the user for guidance.
- **Low fidelity + audit errors remaining** — Pause and ask the user for guidance.

If only the template audit ran (no designs), use audit results alone: pass proceeds, errors after 3 fix iterations proceed with warning.

#### 6. Archive Artifacts

1. Generate a fidelity report using the `showboat-proof` skill, including:
   - Side-by-side screenshots (if visual comparison ran)
   - Template audit summary and violation list (if static audit ran)
2. Store the report in `.superdesign/fidelity_check/report.md`.
3. Commit and push:
   ```bash
   git add .superdesign/fidelity_check/
   git commit -m "docs: add UI fidelity check results for #$ISSUE_NUMBER [$REQ_ID]"
   ```
   Include `[$REQ_ID]` only if $REQ_ID is available.
4. Push the commit.

### Output Format (check)
```
Template Audit: PASS | FAIL | skipped
Visual Fidelity: High | Medium | Low | skipped
Iterations: <N>
Report: .superdesign/fidelity_check/report.md
Commit: <sha>
```

---

### audit-only

Run only the static template audit (no visual comparison).

**Usage**: `ui-fidelity audit-only`

Executes only step 1 (Static Template Audit) from the `check` flow above. Returns audit results without visual comparison.

### Output Format (audit-only)
```
Template Audit: PASS | FAIL | skipped
Errors: <N>
Warnings: <N>
Iterations: <N>
```

---

### compare-only

Run only the visual screenshot comparison (no static audit).

**Usage**: `ui-fidelity compare-only`

Executes only steps 2-5 (Prepare, Capture, Compare, Handle Results) from the `check` flow above. Requires designs to exist in the nano-spec.

### Output Format (compare-only)
```
Visual Fidelity: High | Medium | Low
Dimensions: <summary of ratings>
Iterations: <N>
Report: .superdesign/fidelity_check/report.md
```
