# /req-decompose

Decompose requirements into GitHub issues. Processes a product-phase directory containing `requirements.md` and optionally `architecture.md`, creating one issue per requirement.

## Usage

```
/req-decompose <action> <phase-dir> [--repo owner/repo]
```

## Arguments

- `action` — One of `scan` (preview), `create` (create issues), or `status` (check existing).
- `phase-dir` — Path to the product-phase directory (must contain `requirements.md`).
- `--repo owner/repo` — Target repository. Defaults to the current repo.

## Behavior

Parse `$ARGUMENTS` to extract the action, phase directory, and optional repo flag, then invoke the **req-decompose** skill with `$ACTION`, `$PHASE_DIR`, and `$REPO` set accordingly.

### Actions

- **scan** — Preview the issues that would be created. No GitHub API calls, no files written. Shows each requirement's expanded body, open questions, and label eligibility.
- **create** — Create GitHub issues from `requirements.md`. Issues with zero open questions and no dependencies are auto-labeled `claude-ready` for the dev-loop to pick up. Writes a `manifest.json` for traceability.
- **status** — Check the current state of previously created issues. Shows labels, assignments, and downstream artifacts (nano-spec, BDD feature, PR) for each requirement.
