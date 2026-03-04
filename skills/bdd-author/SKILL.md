---
name: bdd-author
description: Write and automate BDD test specifications. Use "bdd-author write" to generate feature files from issue content, or "bdd-author automate" to generate step definitions from existing feature files.
---

# bdd-author: BDD Test Authoring

Generate BDD feature specifications and automate them with step definitions.

## Arguments
- $ACTION: The action to perform (write, automate)
- $INPUT: Issue content for `write`, or path to feature file for `automate`

## Framework Detection

Before generating any output, detect the project's BDD framework:

1. **Check for existing BDD files:**
   - Look for `*.feature` files anywhere in the project
   - Check for `behave.ini`, `cucumber.js`, `.cucumber`, `jest-cucumber` config
   - Check for `pytest-bdd` in `pyproject.toml`, `setup.cfg`, or `requirements*.txt`

2. **Infer from project language if no BDD framework found:**
   - Python → recommend and use `pytest-bdd`
   - JavaScript/TypeScript → recommend and use `cucumber-js`
   - Ruby → recommend and use `cucumber`
   - Go → recommend and use `godog`
   - Java/Kotlin → recommend and use `cucumber-jvm`

3. **Determine test directory:**
   - Use existing BDD test directory if found
   - Otherwise use `tests/bdd/` (Python), `features/` (Ruby/JS), or equivalent convention

## Traceability

Feature files carry traceability metadata via Gherkin `@` tags. These tags link BDD tests back to requirements, issues, and acceptance criteria.

**Tag conventions:**
- `@REQ-XXX` — links to the originating requirement ID (from req-decompose)
- `@issue-N` — links to the GitHub issue number
- `@AC-N` — links a scenario to a specific acceptance criterion in the issue body

The caller (typically the dev-loop agent) provides the REQ-ID and issue number. If not provided, omit those tags — only add tags for identifiers you actually have.

## Actions

### write
Generate a BDD feature file from issue content. Does NOT write automation code.

**Usage**: `/bdd-author write`

Provide the issue title and body as context (typically passed by the dev-loop agent). The caller should also provide the issue number and REQ-ID if available.

**Steps:**

1. Detect the BDD framework per the detection strategy above.
2. Parse the issue content to identify:
   - The feature being requested
   - Acceptance criteria (explicit or implied)
   - Edge cases and error scenarios
3. Determine the feature file name: use `<req-id>-<slug>.feature` if a REQ-ID is available (e.g., `req-001-user-authentication.feature`), otherwise `<issue-number>-<slug>.feature` (e.g., `42-user-authentication.feature`).
4. Generate a `.feature` file in Gherkin syntax with traceability tags:

```gherkin
@REQ-XXX @issue-N
Feature: <derived from issue title>
  <one-line description derived from issue body>

  Background:
    Given <common preconditions if any>

  @AC-1
  Scenario: <maps to acceptance criterion 1>
    Given <initial state>
    When <action>
    Then <expected outcome>

  @AC-2
  Scenario: <maps to acceptance criterion 2>
    Given <initial state>
    When <problematic action>
    Then <expected error handling>
```

5. Include scenarios for:
   - Each explicit acceptance criterion → one scenario, tagged `@AC-N` matching the criterion's position in the issue body
   - Happy path if not covered by criteria
   - At least one error/edge case scenario
6. Write the feature file to the detected test directory.
7. If the project has no BDD framework installed, note the required dependency but still write the feature file.

### Output Format (write)
```
BDD Framework: <detected or recommended framework>
Feature file: <path to generated .feature file>
Traceability: REQ-XXX → #N (or "no REQ-ID provided")
Scenarios: <count> (<brief list with @AC-N mappings>)

Note: <any setup instructions if framework not yet installed>
```

---

### automate
Generate step definitions / test glue code for an existing feature file.

**Usage**: `/bdd-author automate`

Provide the path to the feature file as context (typically passed by the dev-loop agent).

**Steps:**

1. Read the specified feature file.
2. Detect the BDD framework per the detection strategy above.
3. Extract all unique step patterns (Given/When/Then) from the feature file.
4. Check for existing step definitions to avoid duplicates:
   - Python/pytest-bdd: look in `conftest.py`, `test_*.py`, `*_steps.py`
   - Cucumber: look in `step_definitions/`, `steps/`
5. Generate step definition code for each new step:

**Python (pytest-bdd) example:**
```python
from pytest_bdd import given, when, then, scenarios

scenarios("<feature_file>.feature")

@given("<step text>")
def given_step():
    ...

@when("<step text>")
def when_step():
    ...

@then("<step text>")
def then_step():
    ...
```

**JavaScript (cucumber-js) example:**
```javascript
const { Given, When, Then } = require("@cucumber/cucumber");

Given("<step text>", function () {
  // implementation
});
```

6. Write step definitions to the framework-conventional location:
   - pytest-bdd: alongside test file or in `conftest.py`
   - cucumber: `features/step_definitions/<feature_name>_steps.{js,rb}`
7. Add a `TODO` comment in each step body indicating what needs to be implemented.
8. If the BDD framework dependency is missing, add it:
   - Python: add to `requirements.txt` or `pyproject.toml`
   - JS: `npm install --save-dev @cucumber/cucumber`
   - Note the installation for the user
9. Preserve all `@` traceability tags from the feature file. Step definitions must not strip or ignore `@REQ-XXX`, `@issue-N`, or `@AC-N` tags.

### Output Format (automate)
```
Step definitions: <path to generated file>
Steps automated: <count> (<count> new, <count> existing)
Traceability tags preserved: @REQ-XXX, @issue-N, @AC-1, ...

Dependencies added: <list or "none needed">
```
