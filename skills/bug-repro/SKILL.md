---
name: bug-repro
description: Write a single regression test that reproduces a bug. The test fails on the broken code and passes after the fix. Use "bug-repro write" before implementing the fix.
---

# bug-repro: Bug Reproduction Test

For the `bug` track, the dev-loop replaces full BDD authoring with a single regression test. The test asserts the **fixed** behavior so it fails against the current code and passes after the fix lands. This is the cheapest way to verify both the bug exists and the fix works.

## Arguments
- $ACTION: The action to perform (write)
- $ISSUE_NUMBER: The GitHub issue number (required, used in test naming and traceability)
- $ISSUE_TITLE: The issue title (required)
- $ISSUE_BODY: The realigned issue body (required — bug reports often have "Steps to reproduce")
- $REQ_ID: Requirement ID (optional, included in the test docstring/comment)

## Action

### write

Generate one regression test that reproduces the bug.

**Usage**: `bug-repro write`

**Steps:**

#### 1. Detect the test framework

Same logic as `bdd-author`'s framework detection but for unit/integration tests:

1. Check existing tests:
   - Python: `pytest.ini`, `pyproject.toml [tool.pytest]`, `conftest.py` → pytest
   - JS/TS: `jest.config.*`, `vitest.config.*`, `package.json scripts.test` → jest/vitest
   - Ruby: `spec/spec_helper.rb` → rspec
   - Go: `go.mod` + existing `*_test.go` → standard `testing`
   - Rust: `Cargo.toml` + `tests/` → built-in
   - Java/Kotlin: `pom.xml` / `build.gradle` → JUnit
2. Match the most-used framework in the test directory.

#### 2. Parse the bug report

From $ISSUE_BODY extract:
- **Steps to reproduce** (or equivalent: "Repro", "How to reproduce", "Reproduction")
- **Expected behavior** (the FIXED outcome — this becomes the assertion)
- **Actual behavior** (the broken outcome — this becomes the test setup context, NOT what we assert)
- **Environment / preconditions** (versions, config, data state)

If "Steps to reproduce" is missing, attempt to derive it from the body. If you cannot, return:
```
bug-repro: ABORT
Reason: no reproducible steps in issue #<number>
Action: ask the user for steps to reproduce, or downgrade the track from bug to spike.
```
The dev-loop agent should pause here.

#### 3. Determine test location and name

- Place the test alongside the code that is broken (mirror the existing test directory layout).
- Naming: `test_issue_<number>_<short-slug>.<ext>` (Python) or `issue-<number>-<short-slug>.test.<ext>` (JS/TS) or framework convention.
- The test file holds **one** test function. Bug repros stay focused; downstream `test-loop full` covers the rest.

#### 4. Write the test

The test MUST:

1. **Set up the conditions** described in "Steps to reproduce" using real fixtures, the real entry point, and real dependencies (mocks only at third-party I/O boundaries — same rule as `bdd-author automate`).
2. **Execute the action** that triggers the bug (HTTP request, function call through the public API, CLI invocation, message publish).
3. **Assert the EXPECTED (fixed) behavior**, not the broken behavior. The test must FAIL against `main` and PASS after the fix.
4. Carry traceability: docstring or top-line comment of the form
   `Regression test for #<issue-number> [<REQ-ID if available>] — <one-line bug summary>`.

**Python example:**
```python
def test_issue_42_reset_link_expires_in_one_hour():
    """Regression test for #42 [REQ-007] — reset link did not expire after 1h.

    entry: POST /reset-password via TestClient | observe: HTTP response on second use
    """
    client = TestClient(app)
    # 1. Request a reset link
    res = client.post("/reset-password", json={"email": "alice@example.com"})
    token = extract_token(res.json()["link"])
    # 2. Advance the clock past the documented 1h TTL
    with frozen_time("+1h 1m"):
        # 3. Use the token — it should be rejected
        res2 = client.post("/reset-password/confirm", json={"token": token, "password": "newp"})
        assert res2.status_code == 410  # Gone — link expired
        assert res2.json()["error"] == "link_expired"
```

**JS/TS example:**
```typescript
test("issue #42 — reset link expires in 1h [REQ-007]", async () => {
  // entry: POST /reset-password via supertest | observe: HTTP response on second use
  const res = await request(app).post("/reset-password").send({ email: "alice@example.com" });
  const token = extractToken(res.body.link);

  jest.useFakeTimers().setSystemTime(Date.now() + 60 * 60 * 1000 + 60 * 1000);

  const res2 = await request(app)
    .post("/reset-password/confirm")
    .send({ token, password: "newp" });

  expect(res2.status).toBe(410);
  expect(res2.body.error).toBe("link_expired");
});
```

#### 5. Run the test against current code

Execute the test once before reporting. The test SHOULD fail (because the bug isn't fixed yet). Capture the failure output.

- **If the test fails as expected** → bug is reproduced. Report success.
- **If the test passes** → either the bug is already fixed (close the issue with a comment), or the test isn't actually exercising the bug (rewrite). Report ambiguity to the dev-loop agent.
- **If the test errors out** (import errors, fixture missing) → fix the test setup; do not report success until the test runs cleanly to a failure.

#### 6. Commit

```bash
git add <test-file-path>
git commit -m "test: add reproduction test for #<issue-number> [<REQ-ID>]"
```

Include `[<REQ-ID>]` only if available. Push.

### Output Format (write)
```
Bug reproduction test: <path to test file>
Framework: <detected>
Test: <test function name>
Run result on current main: FAIL (as expected) | PASS (bug already fixed?) | ERROR (setup broken)
Traceability: #<issue-number> [REQ-XXX]

Next step: implement the fix, then run the test runner — the test should turn green.
```

## Notes

- Bug-repro replaces BDD spec authoring on the bug track. There is no `.feature` file for bugs.
- The `test-loop full` step (Step 13 in dev-loop) runs after implementation and includes this regression test alongside the existing suite. No separate `bdd` test loop is needed for the bug track.
- Mark the test file's location in `nano-spec/README.md` Traceability section so future maintainers can find it from the issue.
