---
name: ui-audit
description: Run static analysis on HTML templates for design system violations. Use "ui-audit run" to audit templates, "ui-audit generate-config" to scaffold a project config, or "ui-audit bdd" to generate a BDD feature wrapping the auditor.
---

# ui-audit: Static Template Analysis for Design System Compliance

Scan HTML templates for design system violations without requiring a running server, browser, or database. Catches hardcoded colors, missing ARIA landmarks, class violations, CSS token drift, inline style duplication, and local redefinitions of shared classes.

Works with any HTML templating system (Jinja2, Django, ERB, Handlebars).

## Arguments
- $ACTION: The action to perform (run, generate-config, bdd). Defaults to `run`.
- $TARGET: Optional path to config file or target directory.

## Prerequisites

The `exo` shared library must be importable. Verify by running:

```bash
python -c "from exo.template_auditor import TemplateAuditor; print('OK')"
```

If not found, instruct the user:
```
pip install -e /path/to/exo/lib
```

If prerequisites are missing, stop and report what needs to be installed. Do not proceed without them.

## Actions

### run

Run the template auditor against the current project.

**Usage**: `ui-audit run [config-path]`

**Steps:**

1. Locate the config file:
   - If `$TARGET` is provided and is a file path, use it.
   - Otherwise look for `.template-audit.yaml` in the project root.
   - If no config found, tell the user: "No `.template-audit.yaml` found. Run `ui-audit generate-config` to create one."
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
       # ... populated from the YAML contents
       "rules": {
           "hardcoded_colors": True,
           "aria_landmarks": True,
           # ...
       }
   }

   auditor = from_config(config)
   results = auditor.run_all()
   print(results.summary())
   for v in results.violations:
       print(v)
   raise SystemExit(0 if results.passed else 1)
   ```

4. Report results:

**If all checks pass (exit code 0):**
```
Template Audit: PASS
<summary line from results.summary()>
```
List any warnings if present.

**If errors found (exit code 1):**
```
Template Audit: FAIL
<summary line from results.summary()>

Errors:
  <grouped violations>

Warnings:
  <grouped violations>
```

### Output Format (run)
```
Template Audit: PASS | FAIL
Scanned: <N> templates, <N> rules
Errors: <N>
Warnings: <N>

[Violation details grouped by rule]
```

---

### generate-config

Scan the project and scaffold a `.template-audit.yaml` config file.

**Usage**: `ui-audit generate-config`

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
Review the config and adjust as needed, then run `ui-audit run`.
```

---

### bdd

Generate a BDD feature file and step definitions that wrap the template auditor, so design system checks become part of the project's test suite.

**Usage**: `ui-audit bdd`

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
