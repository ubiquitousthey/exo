---
name: ui-verify
description: Verify UI implementation through static template audit and visual fidelity comparison. Use "ui-verify audit" for static analysis, "ui-verify compare" for visual comparison, "ui-verify check" for the full flow, "ui-verify generate-config" to scaffold config, or "ui-verify bdd" to generate BDD tests for design system rules.
---

# ui-verify: UI Verification

Verify UI implementation quality through static template analysis and visual screenshot comparison against design mockups. Combines design system compliance checking with visual fidelity verification.

## Arguments
- $ACTION: The action to perform (audit, compare, check, generate-config, bdd)
- $NANO_SPEC_PATH: Path to the nano-spec task directory (required for compare, check)
- $BASE_BRANCH: The base branch to diff against (default: `main`)
- $ISSUE_NUMBER: The GitHub issue number (optional, for commit messages)
- $REQ_ID: Requirement ID like REQ-001 (optional)
- $TARGET: Optional path to config file or target directory (for audit, generate-config)

## Prerequisites

For static audit actions (`audit`, `check`, `generate-config`, `bdd`), the `exo` shared library must be importable:

```bash
python -c "from exo.template_auditor import TemplateAuditor; print('OK')"
```

If not found, instruct the user:
```
pip install -e /path/to/exo/lib
```

For visual comparison actions (`compare`, `check`), rodney must be available:
```bash
rodney status
```

If prerequisites are missing, stop and report what needs to be installed. Do not proceed without them.

## Skip Conditions (for `check` action)

**Skip entirely** if BOTH of the following are true:
- The nano-spec `$NANO_SPEC_PATH/README.md` has no UI Design section (no designs exist)
- `git diff --name-only $BASE_BRANCH...HEAD` shows no `*.html` files

If only one condition is met, run the applicable sub-steps.

## Actions

### audit

Run static template analysis for design system violations. Catches hardcoded colors, missing ARIA landmarks, class violations, CSS token drift, inline style duplication, and local redefinitions of shared classes. Works with any HTML templating system (Jinja2, Django, ERB, Handlebars).

**Usage**: `ui-verify audit [config-path]`

**Steps:**

1. Locate the config file:
   - If `$TARGET` is provided and is a file path, use it.
   - Otherwise look for `.template-audit.yaml` in the project root.
   - If no config found, tell the user: "No `.template-audit.yaml` found. Run `ui-verify generate-config` to create one."
2. Read the YAML config file.
3. Write and execute a Python script that:
   - Constructs the config as a Python dict literal (to avoid requiring `pyyaml` at runtime)
   - Imports `from exo.template_auditor import from_config`
   - Calls `auditor = from_config(config)`
   - Calls `results = auditor.run_all()`
   - Prints `results.summary()`
   - Prints each violation, grouped by rule then severity
   - Exits with code 1 if `not results.passed`

   Example script structure:
   ```python
   from exo.template_auditor import from_config

   config = {
       "templates_dir": "app/",
       "base_template": "app/templates/base.html",
       "allowed_colors": ["#0d1421", "#c09a3a"],
       "rules": {
           "hardcoded_colors": True,
           "aria_landmarks": True,
       }
   }

   auditor = from_config(config)
   results = auditor.run_all()
   print(results.summary())
   for v in results.violations:
       print(v)
   raise SystemExit(0 if results.passed else 1)
   ```

4. Report results.

### Output Format (audit)
```
Template Audit: PASS | FAIL
Scanned: <N> templates, <N> rules
Errors: <N>
Warnings: <N>

[Violation details grouped by rule]
```

---

### compare

Run visual screenshot comparison against superdesign mockups. Requires designs to exist in the nano-spec.

**Usage**: `ui-verify compare`

**Steps:**

#### 1. Prepare Comparison Pairs
1. Read `$NANO_SPEC_PATH/README.md` UI Design section.
2. Map each design file to its corresponding implementation URL (route or page).
3. Build a list of comparison pairs: `(design HTML path, implementation URL)`.

#### 2. Capture Screenshots
For each comparison pair:
1. Use rodney to screenshot the superdesign HTML file (`file://` path to the `.superdesign/design_iterations/*.html` file).
2. Use rodney to screenshot the running implementation page at its URL.
3. Store all screenshots in `.superdesign/fidelity_check/`.

#### 3. Visual Comparison
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

#### 4. Handle Results
- **High fidelity** — Log pass, proceed.
- **Medium or Low fidelity** — Fix the implementation to better match the design, re-capture screenshots, and re-evaluate. **Max 3 iterations.**
  - After 3 iterations: **Medium** proceeds with a warning. **Low** pauses and asks the user for guidance.

### Output Format (compare)
```
Visual Fidelity: High | Medium | Low
Dimensions: <summary of ratings>
Iterations: <N>
Report: .superdesign/fidelity_check/report.md
```

---

### check

Run the full verification flow: static template audit + visual comparison + fix loops + artifact archiving.

**Usage**: `ui-verify check`

**Steps:**

#### 1. Static Template Audit
1. Check if `git diff --name-only $BASE_BRANCH...HEAD` includes `*.html` files. If not, skip.
2. Check for `.template-audit.yaml` in the project root. If absent, log a note and skip.
3. Run the `audit` action logic.
4. If errors are found: fix violations, re-run. **Max 3 iterations.** After 3, log remaining as warnings.
5. Commit any fixes:
   ```bash
   git add <fixed-template-files>
   git commit -m "fix: address template audit violations for #$ISSUE_NUMBER"
   ```
6. Push the commit.

**If no designs exist** (no UI Design section in nano-spec): skip visual comparison, jump to Handle Results.

#### 2. Visual Comparison
Run the `compare` action logic (prepare pairs, capture screenshots, compare dimensions).

#### 3. Handle Combined Results
Combine template audit status with visual fidelity rating:

- **High fidelity + audit pass** — Log pass, proceed.
- **Medium/High fidelity + audit errors remaining** — Proceed with a warning logged.
- **Medium or Low fidelity** — Fix, re-capture, re-evaluate. **Max 3 iterations.**
  - After 3 iterations: **Medium** proceeds with warning. **Low** pauses for user guidance.
- **Low fidelity + audit errors remaining** — Pause for user guidance.

If only the template audit ran (no designs), use audit results alone.

#### 4. Archive Artifacts
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

### Output Format (check)
```
Template Audit: PASS | FAIL | skipped
Visual Fidelity: High | Medium | Low | skipped
Iterations: <N>
Report: .superdesign/fidelity_check/report.md
Commit: <sha>
```

---

### generate-config

Scan the project and scaffold a `.template-audit.yaml` config file.

**Usage**: `ui-verify generate-config`

**Steps:**

1. Scan the project for template-related files and patterns:
   - **Template directories**: Look for directories containing `*.html` files (common locations: `templates/`, `app/`, `src/`, `pages/`, `views/`)
   - **Base/layout template**: Look for files named `base.html`, `layout.html`, `_layout.html`, or containing `{% block %}` / `{{ yield }}` / `<%= yield %>` patterns
   - **CSS custom properties**: Search for `:root` blocks to extract the color palette and token names
   - **Existing utility classes**: Scan CSS/HTML for recurring class definitions
   - **Standalone templates**: Look for HTML files that define their own `:root` block (not extending base)

2. Generate `.template-audit.yaml` in the project root with:
   - `templates_dir` pointing to the discovered template root
   - `base_template` pointing to the discovered layout file
   - `allowed_colors` populated from `:root` color definitions
   - `standalone_templates` listing self-contained HTML files
   - `rules` section with sensible defaults enabled:
     - `hardcoded_colors: true`
     - `aria_landmarks: true`
     - Discovered utility classes added to `base_classes` and `no_redefinition`

3. Present the generated config to the user for review before writing. Explain each section and what was discovered.

### Output Format (generate-config)
```
Discovered:
  Template directory: <path>
  Base template: <path>
  Color tokens: <count> colors from :root
  Standalone templates: <count>
  Utility classes: <list>

Generated: .template-audit.yaml
Review the config and adjust as needed, then run `ui-verify audit`.
```

---

### bdd

Generate a BDD feature file and step definitions that wrap the template auditor, so design system checks become part of the project's test suite.

**Usage**: `ui-verify bdd`

**Steps:**

1. Verify `.template-audit.yaml` exists. If not, instruct user to run `generate-config` first.
2. Read the config to understand which rules are enabled.
3. Generate a feature file (e.g., `features/ui-audit.feature` or project-appropriate location):

   ```gherkin
   @ui-audit
   Feature: Design system compliance
     HTML templates follow the project's design system rules.

     Scenario: No hardcoded colors outside design tokens
       When I run the template auditor color check
       Then there are no color violations

     Scenario: ARIA landmarks present in base template
       When I run the template auditor ARIA check
       Then there are no ARIA violations

     # ... one scenario per enabled rule
   ```

4. Generate step definitions that import the auditor and run individual rules:

   ```python
   from exo.template_auditor import from_config
   import yaml

   @given("the template auditor config")
   def load_config(context):
       with open(".template-audit.yaml") as f:
           context.auditor = from_config(yaml.safe_load(f))

   @when("I run the template auditor color check")
   def run_color_check(context):
       context.violations = context.auditor.run_rule("hardcoded-color")

   @then("there are no color violations")
   def assert_no_violations(context):
       errors = [v for v in context.violations if v.severity == "error"]
       assert not errors, "\n".join(str(v) for v in errors)
   ```

5. Report what was generated and where.

### Output Format (bdd)
```
Generated:
  Feature: <path to feature file>
  Steps: <path to step definitions>
  Scenarios: <count> (one per enabled rule)

Run with: <project's test command>
```
