# /ui-audit

Run static analysis on HTML templates for design system violations.

## Usage

```
/ui-audit [action] [target]
```

## Arguments

- `action` — One of `run` (default), `generate-config`, or `bdd`.
- `target` — Optional path to config file or target directory.

## Behavior

Parse `$ARGUMENTS` to extract the action and target, then invoke the **ui-audit** skill with `$ACTION` set to the action and `$TARGET` set to the target.

### Actions

- **run** — Run the template auditor against the current project. Looks for `.template-audit.yaml` in the project root. If no config exists, prompts to run `generate-config` first.
- **generate-config** — Scan the project codebase and generate a `.template-audit.yaml` config file interactively.
- **bdd** — Generate a BDD feature file and step definitions wrapping the auditor, so design system checks become part of the project's test suite.
