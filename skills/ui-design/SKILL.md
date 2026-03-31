---
name: ui-design
description: Detect if a feature requires UI work and orchestrate superdesign to generate designs. Use "ui-design detect" to check signals, or "ui-design generate" to run the full design flow.
---

# ui-design: UI Design Orchestration

Determine whether a feature needs UI design work and, if so, gather context and invoke superdesign to generate designs.

## Arguments
- $ACTION: The action to perform (detect, generate)
- $ISSUE_TITLE: The issue title
- $ISSUE_BODY: The issue body content
- $BDD_FEATURE_PATH: Path to the BDD feature file (optional)
- $NANO_SPEC_PATH: Path to the nano-spec task directory (optional)
- $ISSUE_NUMBER: The GitHub issue number (optional, for commit messages)
- $REQ_ID: Requirement ID like REQ-001 (optional, for traceability)

## Actions

### detect

Check whether the feature requires UI work. Returns a determination without generating designs.

**Usage**: `ui-design detect`

**Steps:**

1. **Explicit design reference**: Check if $ISSUE_BODY contains a link to an existing superdesign file (e.g., a path like `.superdesign/design_iterations/*.html` or a reference to a superdesign project). If found, return `ui_needed: true, existing_design: <path>`.
2. **Issue signals**: Check if $ISSUE_TITLE or $ISSUE_BODY mentions UI, frontend, page, screen, dashboard, form, component, layout, modal, dialog, widget, or similar visual terms.
3. **Project signals**: Check if the project's `CLAUDE.md` references superdesign, or a `.superdesign/` directory exists in the project.
4. **BDD signals**: If $BDD_FEATURE_PATH is provided, check if the feature file contains scenarios involving user-visible interactions (clicking, viewing, navigating, filling forms).

If none of these signals are present, return `ui_needed: false`.

### Output Format (detect)
```
UI Design Needed: yes | no
Signals: <which signals matched, or "none">
Existing Design: <path, if found> | none
```

---

### generate

Run the full design flow: detect, check prerequisites, gather context, invoke superdesign, and update the nano-spec.

**Usage**: `ui-design generate`

**Steps:**

1. Run the `detect` logic above. If `ui_needed: false`, report that and stop.
2. If an existing design was found in the issue body, skip generation — use that design directly and proceed to step 5.

#### Prerequisites
3. Verify superdesign is available:
   - Check if the project's `CLAUDE.md` has superdesign configuration or rules.
   - Check if a `.superdesign/` directory exists in the project.
   - If neither exists, report that superdesign is not configured for this project and stop.

#### Gather Context
4. Collect inputs for the design prompt:
   - The issue title and acceptance criteria from $ISSUE_BODY
   - Relevant BDD scenarios from $BDD_FEATURE_PATH (especially those describing what the user should see)
   - Existing UI patterns in the project (scan for similar pages/components)
   - Any design references or mockup links in $ISSUE_BODY

#### Generate Designs
5. Invoke superdesign to generate UI designs:
   - Craft a design prompt from the gathered context, describing the screen(s) or component(s) needed.
   - Use superdesign to generate designs. Superdesign creates HTML files in `.superdesign/design_iterations/` with Tailwind CSS styling.
   - Designs are generated as `{design_name}_{n}.html` files with variations for review.

#### Update Nano-spec
6. If $NANO_SPEC_PATH is provided, add a **UI Design** section to `$NANO_SPEC_PATH/README.md` documenting:
   - Design file paths (relative to project root)
   - Brief description of what each design shows
   - If an existing design was referenced from the issue, note it as the source design
7. Update `$NANO_SPEC_PATH/todo.md` implementation phases to reference the designs — add notes about which design to implement in the relevant phase.

#### Commit
8. Commit the designs and nano-spec updates:
   ```bash
   git add .superdesign/design_iterations/ $NANO_SPEC_PATH
   git commit -m "design: add superdesign UI mockups for #$ISSUE_NUMBER [$REQ_ID]"
   ```
   Include `[$REQ_ID]` only if $REQ_ID is available.
9. Push the commit.

### Output Format (generate)
```
UI Design: generated | skipped | existing
Design files: <list of paths>
Nano-spec updated: yes | no
Commit: <sha>
```
