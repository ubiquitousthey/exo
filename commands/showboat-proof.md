# /showboat-proof

Generate executable proof documents that visually demonstrate features work using showboat and rodney.

## Usage

```
/showboat-proof <action> [target]
```

## Arguments

- `action` — One of `prove`, `verify`, or `audit`.
- `target` — Feature description, proof file path, or URL depending on action.

## Behavior

Parse `$ARGUMENTS` to extract the action and target, then invoke the **showboat-proof** skill with `$ACTION` set to the action and `$TARGET` set to the target.

### Actions

- **prove** — Create a showboat demo document proving a feature works. If no target is given, use context from recent work (git diff, BDD feature files, issue content).
- **verify** — Re-run an existing proof document to confirm it still passes. Target should be a proof file path, or the skill will search for proof files.
- **audit** — Run an accessibility audit on a web page. Target should be a URL, or the project's dev server will be used.
