---
name: bdd-author
description: Write and automate BDD test specifications. Use "bdd-author write" to generate feature files from issue content, "bdd-author automate" to generate step definitions, or "bdd-author guard" to scan step definitions for user-perspective anti-patterns.
---

# bdd-author: BDD Test Authoring

Generate BDD feature specifications and automate them with step definitions.

## Arguments
- $ACTION: The action to perform (write, automate, guard)
- $INPUT: Issue content for `write`, path to feature file for `automate`, path(s) to step definition file(s) for `guard`

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

#### User-Perspective Rule

Every `When` step must be an action a real actor takes against the system's real entry point: HTTP request, CLI invocation, UI interaction, message publish, scheduled trigger, file drop. Every `Then` step must be an outcome that actor (or another observable role) can see, receive, or measure.

GOOD:
```gherkin
When the user submits the reset form with "alice@example.com"
Then the user receives an email at "alice@example.com" within 60 seconds
And the email body contains a single-use reset link
```

BAD (rewrite before authoring):
```gherkin
When the AuthService.reset_password method is called    # internal call, not a user action
Then the response JSON has a "token" key                # schema check, not observable behavior
And the mock email_sender was called with the user      # mock-on-mock, not a real outcome
```

Each `@AC-N`-tagged scenario must trace to an AC that already passes the user-perspective rule (see `req-decompose` and `nano-spec`). If the AC reads as "implement endpoint X" or "add column Y", **stop and report**: the AC needs to be rewritten upstream before authoring a scenario for it. Do not paper over an implementation-shaped AC by inventing a user wrapper.

**Steps:**

1. Detect the BDD framework per the detection strategy above.
2. Parse the issue content to identify:
   - The feature being requested
   - Acceptance criteria (explicit or implied)
   - Edge cases and error scenarios
3. **Validate each AC against the user-perspective rule.** If any AC is implementation-shaped, return a report listing the offending criteria and stop without writing the feature file.
4. Determine the feature file name: use `<req-id>-<slug>.feature` if a REQ-ID is available (e.g., `req-001-user-authentication.feature`), otherwise `<issue-number>-<slug>.feature` (e.g., `42-user-authentication.feature`).
5. Generate a `.feature` file in Gherkin syntax with traceability tags:

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

6. Include scenarios for:
   - Each explicit acceptance criterion → one scenario, tagged `@AC-N` matching the criterion's position in the issue body
   - Happy path if not covered by criteria
   - At least one error/edge case scenario
7. Write the feature file to the detected test directory.
8. If the project has no BDD framework installed, note the required dependency but still write the feature file.

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

#### Step Definition Rules

Step bodies MUST:

1. **Drive the system through a real entry point.** Acceptable: HTTP request to a running server (or test client over the real WSGI/ASGI app), CLI subprocess, UI driver (Playwright/Selenium), publishing to the real broker, writing the real input file. **Not acceptable**: calling an internal function with mocks for everything around it.
2. **Assert on observable outputs.** Acceptable: response status + body values, persisted state read back through the public API, queue contents read by a real consumer, file written, email captured by a real test SMTP sink. **Not acceptable**: asserting that a mock was called, or that the response matches a JSON schema with no value-level assertions.
3. **Mock only third-party I/O at the system boundary.** External APIs you do not own, paid services, clocks, randomness — those may be mocked. Mocking your own service or repository layers from a BDD step is a guard violation.
4. **Place a one-line comment at the top of each step body** stating which entry point it drives and which observable output it asserts on. The `bdd-author guard` action verifies this comment is present.

These rules are checked by the `guard` action. Violations block the dev-loop pipeline.

**Steps:**

1. Read the specified feature file.
2. Detect the BDD framework per the detection strategy above.
3. Extract all unique step patterns (Given/When/Then) from the feature file.
4. Check for existing step definitions to avoid duplicates:
   - Python/pytest-bdd: look in `conftest.py`, `test_*.py`, `*_steps.py`
   - Cucumber: look in `step_definitions/`, `steps/`
5. Generate step definition code for each new step. Each step body MUST start with a one-line comment of the form `# entry: <real entry point> | observe: <observable output>` (or `// entry: ... | observe: ...` for JS/TS). Example:

**Python (pytest-bdd) example:**
```python
from pytest_bdd import given, when, then, scenarios
from starlette.testclient import TestClient
from app.main import app

scenarios("<feature_file>.feature")

@given("a registered user with email \"alice@example.com\"")
def given_registered_user(db):
    # entry: direct DB seed (test fixture) | observe: row in users table
    db.execute("INSERT INTO users(email) VALUES ('alice@example.com')")

@when("the user submits the reset form with \"alice@example.com\"")
def when_submit_reset(context):
    # entry: POST /reset-password via TestClient | observe: HTTP response
    client = TestClient(app)
    context.response = client.post("/reset-password", json={"email": "alice@example.com"})

@then("the user receives a reset email at \"alice@example.com\" within 60 seconds")
def then_reset_email_received(smtp_sink):
    # entry: read from real test SMTP sink | observe: email visible to recipient
    msg = smtp_sink.wait_for(to="alice@example.com", timeout=60)
    assert "reset" in msg.subject.lower()
    assert "/reset?token=" in msg.body
```

**JavaScript (cucumber-js) example:**
```javascript
const { Given, When, Then } = require("@cucumber/cucumber");
const request = require("supertest");
const app = require("../../src/app");

When("the user submits the reset form with {string}", async function (email) {
  // entry: POST /reset-password via supertest | observe: HTTP response
  this.response = await request(app).post("/reset-password").send({ email });
});

Then("the user receives a reset email at {string} within 60 seconds", async function (email) {
  // entry: read from test SMTP sink | observe: email visible to recipient
  const msg = await this.smtp.waitFor({ to: email, timeoutMs: 60000 });
  expect(msg.body).toMatch(/\/reset\?token=/);
});
```

6. Write step definitions to the framework-conventional location:
   - pytest-bdd: alongside test file or in `conftest.py`
   - cucumber: `features/step_definitions/<feature_name>_steps.{js,rb}`
7. **Each step body must include the `entry: ... | observe: ...` comment.** Implement the body using a real entry point per the Step Definition Rules. If the implementation isn't ready, write the body to drive the real entry point and assert on the observable output anyway — the test can fail until the implementation lands. Do NOT replace the body with a `TODO` and a `pass`.
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

---

### guard

Scan step definition files for user-perspective anti-patterns. Hard fails the dev-loop pipeline on findings.

**Usage**: `/bdd-author guard`

Provide the path(s) to the step definition file(s) (typically passed by the dev-loop agent after `automate` runs). Optionally pass the feature file path for context.

**Anti-patterns checked**

For each step body in each step-definition file, flag:

1. **Mock-on-mock.** The body's only assertions are mock-call assertions. Detection regexes (per language):
   - Python: `\.assert_called(_with|_once|_once_with)?\(`, `\.called\b`, `assert_not_called`, `\.call_count\b`
   - JS/TS: `\.toHaveBeenCalled(With|Times)?\(`, `\.toHaveBeenLastCalledWith\(`, `expect\(.*\.mock\)`
   - Ruby/RSpec: `have_received\(`, `should have_received`
   - Java/Kotlin (Mockito): `verify\(.*\)\.`, `Mockito\.verify`
   Trigger if these matches exist AND the step body contains no other assertion (`assert`, `expect(...)\.(toBe|toEqual|toMatchObject|toContain)`, `should ==`, `assertThat`).

2. **Schema-only.** The only assertion is a schema validation. Detection regexes:
   - Python: `validate_schema\(`, `jsonschema\.validate\(`, `pydantic` model parse with no field assertion afterwards
   - JS/TS: `\.toMatchSchema\(`, `ajv\.validate\(`, `joi\.\w+\.validate\(`, `zod.*\.parse\(` with no field assertion
   - General: any call with `schema` in the function name and no value-level assertion in the same body
   Trigger if the body validates structure but never asserts a specific value, status code, or piece of state.

3. **No real entry point.** The step body calls into project code directly without going through an entry point. Heuristic:
   - Body contains a call to a project module (anything imported from `src/`, `app/`, `lib/`, or the project's package).
   - Body does NOT import or use any of: `requests`, `httpx`, `urllib`, `TestClient`, `supertest`, `fetch`, `axios`, `subprocess`, `Popen`, `page`, `browser`, `playwright`, a broker client (`kafka`, `redis`, `pika`, `nats`), or filesystem I/O for a real input file.
   Trigger if the body bypasses the entry point boundary.

4. **Missing entry/observe comment.** No comment matching `(?i)(?:#|//)\s*entry:.+\|\s*observe:.+` within the first 3 lines of the step body. Trigger always.

**Steps:**

1. For each path in $INPUT, read the file.
2. Parse step bodies. A step body is the function/lambda body following a `@given`/`@when`/`@then` decorator (Python) or the callback inside `Given/When/Then(...)` (JS/Ruby).
3. Run each anti-pattern check against each step body. Record findings as `(file, line, anti_pattern, snippet)`.
4. Print the structured report.

**Important**: The guard reports findings; it does NOT auto-fix. The dev-loop agent runs the auto-fix loop by re-invoking `bdd-author automate` with the guard report as input.

### Output Format (guard)
```
BDD Guard: PASS | FAIL
Files scanned: <count>
Step bodies scanned: <count>
Findings: <count>

Findings:
  - <file>:<line> [<anti-pattern>] <step text>
    snippet: <first ~80 chars of the offending body>
    why: <one-line explanation>
```

If `BDD Guard: PASS`, no anti-patterns were found and the dev-loop pipeline may proceed. If `FAIL`, the dev-loop pipeline must hard-fail and trigger the auto-fix loop.
