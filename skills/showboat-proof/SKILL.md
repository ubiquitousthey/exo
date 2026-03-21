---
name: showboat-proof
description: Generate executable proof documents that visually demonstrate features work. Uses showboat for document construction and rodney for browser automation/screenshots. Use "showboat-proof prove" to create proof, "showboat-proof verify" to re-run existing proofs, or "showboat-proof audit" for accessibility audits.
---

# showboat-proof: Executable Proof Documents

Generate repeatable, human-readable proof that implemented features actually work — not just that tests pass.

## Arguments
- $ACTION: The action to perform (prove, verify, audit)
- $TARGET: Feature description, proof file path, or URL depending on action

## Prerequisites

Before generating any output, check that required tools are available:

1. **showboat**: Run `showboat --version`. If not found, instruct the user:
   ```
   uv tool install showboat
   ```
2. **rodney** (only for web proofs and audits): Run `rodney status`. If not found, instruct the user:
   ```
   uv tool install rodney
   ```

If prerequisites are missing, stop and report what needs to be installed. Do not proceed without them.

## Proof Type Detection

Determine whether the feature requires CLI proof or web proof:

- **CLI proof**: The feature is a command-line tool, library API, data pipeline, or script. Uses `showboat exec` to run commands and capture output.
- **Web proof**: The feature involves a web interface, UI component, or browser-accessible endpoint. Uses `rodney` for browser automation and `showboat image` for screenshots.

Detection heuristic:
1. If $TARGET mentions a URL, port, browser, page, UI, dashboard, or frontend → web proof
2. If the project has a dev server script (`npm run dev`, `python manage.py runserver`, etc.) and the feature involves user-facing changes → web proof
3. Otherwise → CLI proof

## Traceability

Proof documents carry traceability metadata linking back to requirements, issues, and BDD features.

**Discover links by checking:**
- Recent git log for issue references (`#N`)
- BDD feature files in the project for `@REQ-XXX` and `@issue-N` tags
- nano-spec task folders for related README.md with traceability sections
- User-provided context

**Header format:**
```markdown
- **Requirement:** REQ-XXX (if known)
- **Feature file:** path/to/feature.feature (if exists)
- **Issue:** #N (if known)
```

Only include traceability lines for identifiers you actually have. Do not fabricate IDs.

## Proof Directory

Store proof documents in this location:
1. If `proofs/` directory exists in the project → `proofs/<feature-slug>/README.md`
2. If a nano-spec task folder exists for this feature → `tasks/<task-name>/proof.md`
3. Otherwise → create `proofs/<feature-slug>/README.md`

Image files (screenshots) are stored alongside the proof document in the same directory.

## Actions

### prove

Create a showboat demo document proving a feature works.

**Usage**: `/showboat-proof prove`

Provide a description of the feature to prove, or rely on context from recent work (git diff, BDD feature files, issue content).

**Steps:**

1. Check prerequisites per above.
2. Determine proof type (CLI or web).
3. Gather context about the feature:
   - Read recent git diff to understand what was implemented
   - Look for related BDD feature files and extract scenarios
   - Check for related nano-spec tasks
   - Use $TARGET or conversation context as the feature description
4. Determine the proof directory per the rules above.
5. Build the proof document using showboat commands:

**For CLI proofs:**

```bash
showboat init <proof-file> "<Feature Name> Proof"
showboat note <proof-file> "Proving that <feature description> works as specified."
```

Then for each acceptance criterion or key behavior:

```bash
showboat note <proof-file> "## <Criterion description>"
showboat exec <proof-file> bash '<command that exercises the feature>'
```

**For web proofs:**

```bash
showboat init <proof-file> "<Feature Name> Proof"
showboat note <proof-file> "Proving that <feature description> works as specified."
```

Start the browser and dev server:

```bash
rodney start
# Start the dev server if needed (detect from package.json scripts, Makefile, etc.)
showboat exec <proof-file> bash '<start dev server command> &'
# Wait for server readiness
rodney open <url>
rodney waitstable
```

Then for each acceptance criterion:

```bash
showboat note <proof-file> "## <Criterion description>"
# Perform interactions
rodney click "<selector>"
rodney input "<selector>" "<value>"
rodney waitstable
# Capture visual proof
rodney screenshot <image-file>
showboat image <proof-file> '<image-file>'
# Assert expected state
rodney assert "<js expression>" "<expected value>"
showboat exec <proof-file> bash 'rodney assert "<js expression>" "<expected value>" && echo "PASS"'
```

After all criteria:

```bash
# Clean up
rodney stop  # if web proof
# Kill dev server if started
```

6. Each acceptance criterion from the BDD feature file (if present) should map to a section in the proof document, with the `@AC-N` tag noted.
7. Include both positive demonstrations (it works) and meaningful assertions (the output/state is correct).

**Guidelines for proof quality:**
- Proofs must be **specific**: show actual output, actual screenshots, actual data — not just "it ran without errors"
- Proofs must be **repeatable**: another person (or `showboat verify`) can re-run them and get the same results
- Proofs must be **readable**: a reviewer who hasn't seen the code should understand what's being demonstrated
- Prefer capturing meaningful state over trivial assertions (e.g., screenshot showing filtered results, not just "page loaded")
- Add narrative notes between steps explaining what is being demonstrated and why it matters

### Output Format (prove)
```
Proof type: CLI | Web
Proof document: <path to generated proof file>
Traceability: REQ-XXX → #N → feature.feature (or subset)
Sections: <count> (<brief list of what was demonstrated>)
Screenshots: <count> (web proofs only)

Re-verify with: showboat verify <proof-file>
```

---

### verify

Re-run an existing proof document to confirm it still passes.

**Usage**: `/showboat-proof verify`

Provide the path to the proof document, or let the skill find proof files in `proofs/` or `tasks/*/proof.md`.

**Steps:**

1. Check that showboat is installed.
2. Locate the proof file:
   - Use $TARGET if it's a file path
   - Otherwise search for proof files in `proofs/` and `tasks/*/proof.md`
   - If multiple proofs found, list them and ask which to verify
3. Run verification:
   ```bash
   showboat verify <proof-file>
   ```
4. If rodney is needed (proof contains rodney commands), ensure it's installed and start it before verification.
5. Report results:
   - If all outputs match → report PASS
   - If outputs differ → show the diffs and explain what changed
   - If commands fail → report which steps broke and suggest investigation

**Optionally**, if the user requests it, update the proof with fresh output:
```bash
showboat verify <proof-file> --output <proof-file>
```

### Output Format (verify)
```
Proof: <path>
Result: PASS | FAIL
Steps executed: <count>
Steps matching: <count>

Diffs: (if any)
  - Step N: <summary of difference>
```

---

### audit

Run an accessibility audit on a web page, producing a showboat proof document with findings.

**Usage**: `/showboat-proof audit`

Provide a URL to audit, or use the project's dev server.

**Steps:**

1. Check that both showboat and rodney are installed.
2. Determine the target URL:
   - Use $TARGET if it's a URL
   - Otherwise detect and start the project's dev server, use its URL
3. Initialize the proof document:
   ```bash
   showboat init <proof-file> "Accessibility Audit: <page title or URL>"
   ```
4. Start rodney and navigate:
   ```bash
   rodney start
   rodney open <url>
   rodney waitstable
   ```
5. Capture baseline screenshot:
   ```bash
   rodney screenshot <baseline-image>
   showboat image <proof-file> '<baseline-image>'
   ```
6. Extract accessibility tree:
   ```bash
   rodney ax-tree --json
   ```
7. Run the following checks, documenting each finding in the proof:

   **Document structure:**
   - Document language (`lang` attribute present)
   - Heading hierarchy (H1 → H2 → H3, no skipped levels)
   - Landmark regions (banner, navigation, main, contentinfo)
   - Skip navigation link present

   **Interactive elements:**
   - All form inputs have accessible labels (`rodney ax-find --role textbox`, etc.)
   - Buttons have accessible names (`rodney ax-find --role button`)
   - Links have visible text content (`rodney ax-find --role link`)
   - Focus indicators visible (`rodney focus "<selector>"` + screenshot)

   **Media and content:**
   - Images have alt text
   - Color contrast (extract foreground/background colors via JS)

   For each check:
   ```bash
   showboat note <proof-file> "### <Check name>"
   showboat exec <proof-file> bash 'rodney <relevant command>'
   # Add PASS/FAIL note based on result
   showboat note <proof-file> "<PASS or FAIL with explanation>"
   ```

8. Capture focus-state screenshots for key interactive elements:
   ```bash
   rodney focus "<selector>"
   rodney screenshot <focus-image>
   showboat image <proof-file> '<focus-image>'
   ```

9. Write a summary section with pass/fail counts.
10. Clean up:
    ```bash
    rodney stop
    ```

### Output Format (audit)
```
Audit: <URL>
Proof document: <path>
Checks: <pass count> passed, <fail count> failed, <total> total

Issues found:
  - <issue 1 summary>
  - <issue 2 summary>

Re-verify with: showboat verify <proof-file>
```
