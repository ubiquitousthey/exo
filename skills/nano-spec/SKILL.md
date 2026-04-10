---
name: nano-spec
description: Manage task specifications with nano-spec (create, status, update). Supports natural language like "create a task spec for..." or "help me plan a task".
---

# nano-spec: Manage task specifications

A lightweight task specification tool that scales documentation to task complexity. Small tasks get minimal docs; complex tasks get full specs.

## Arguments
- $ACTION: The action to perform (create, status, update)
- $TASK_NAME: The task folder name (kebab-case recommended)
- $DESCRIPTION: Brief description (required for create, optional for others)

## Actions

### create
Create a new nano-spec task pack.

**Usage**: `/nano-spec create my-task "Task description"`

#### Step 1 — Assess Complexity

Before generating any files, evaluate the task to determine its size:

| Signal | Small | Medium | Large |
|--------|-------|--------|-------|
| Files likely changed | 1-3 | 4-10 | 10+ |
| New concepts introduced | 0 | 1-2 | 3+ |
| External integrations | 0 | 0-1 | 2+ |
| Data model changes | none | minor | new models or migrations |
| Cross-cutting concerns | none | 1 (e.g., auth, logging) | multiple |
| Ambiguity in requirements | low | some open questions | significant unknowns |

Classify as **small**, **medium**, or **large**.

#### Step 2 — Generate Files

Create folder `tasks/$TASK_NAME/` if tasks/ exists, otherwise create at project root.

Generate files based on complexity:

| File | Small | Medium | Large |
|------|-------|--------|-------|
| `README.md` | Minimal | Standard | Full |
| `todo.md` | Always | Always | Always |
| `doc.md` | Skip | Only if decisions or open questions exist | Full |
| `log.md` | Skip | Always | Always |

---

#### README.md

**Small tasks** — brief, no boilerplate sections:
```markdown
# {Task Name}

{1-2 sentences: what and why}

## Goals
- {Goal}

## Traceability
- **Source**: {#issue or REQ-ID}
```

**Medium tasks** — add scope and dependencies:
```markdown
# {Task Name}

## Background
{2-3 sentences: what problem, why now}

## Goals
- {Goal 1}
- {Goal 2}

## Scope
- In: {what's included}
- Out: {what's explicitly excluded}

## Dependencies
- {Dependency, if any}

## Traceability
- **Source**: {#issue or REQ-ID}
- **BDD Feature**: {path, if any}
```

**Large tasks** — full spec with resources:
```markdown
# {Task Name}

## Background
{Why does this task exist? What problem are we solving?}

## Goals
- {Goal 1}
- {Goal 2}

## Scope

### In Scope
- {What's included}

### Out of Scope
- {What's NOT included - be explicit}

## Dependencies
- [ ] {Dependency 1}

## Traceability
- **Source**: {#issue or REQ-ID}
- **BDD Feature**: {path, if any}

## Resources
- {Links to related docs or references}
```

---

#### todo.md

Always generated. Scale the detail:

**Small tasks:**
```markdown
# TODO

## Implementation
- [ ] {Task 1}
- [ ] {Task 2}

## Acceptance Criteria
- [ ] {Criterion 1}
```

**Medium/Large tasks:**
```markdown
# TODO

## Research
- [ ] {Research item, if unknowns exist}

## Implementation
- [ ] {Phase 1: description}
- [ ] {Phase 2: description}

## Verification
- [ ] {Verification step}

---

## Acceptance Criteria

### Must Have
- [ ] {Criterion 1 - specific, measurable}

### Nice to Have
- [ ] {Optional criterion}
```

---

#### doc.md

**Skip for small tasks.** For medium tasks, only create if there are key decisions to record or open questions to resolve. For large tasks, always create.

**Do NOT include code blocks** unless the task involves:
- Complex algorithmic logic that needs upfront design
- Complex data modeling (new schemas, migrations, entity relationships)
- Non-obvious interface contracts between systems

When code is warranted, keep it minimal — pseudocode or type signatures, not full implementations.

```markdown
# {Task Name} - Technical Document

## Summary
{One paragraph summary of the approach}

## Key Decisions

### Decision 1: {Title}
- **Options considered**: A, B, C
- **Chosen**: B
- **Rationale**: {Why B?}

## Open Questions
- [ ] {Unresolved question}

## References
- {Link}
```

Add a **Technical Details** section with architecture diagrams or schema definitions only when the task involves complex data modeling or multi-component coordination. Omit it otherwise.

---

#### log.md

**Skip for small tasks.** For medium/large tasks:

```markdown
# Development Log

## {YYYY-MM-DD}

### Done
- Task created

### Notes
- {Discoveries, learnings}
```

---

### Output Format (create)

After creating files, summarize:
```
Created nano-spec: tasks/$TASK_NAME/
Complexity: small | medium | large

Files:
- README.md  (background, goals)
- todo.md    (X tasks, Y acceptance criteria)
- doc.md     (technical decisions)     ← if generated
- log.md     (initialized)            ← if generated

Next: Review and refine the generated spec
```

---

### status
Show current progress of a task.

**Usage**: `/nano-spec status my-task`

1. Read `tasks/$TASK_NAME/todo.md` and `log.md` (if exists)
2. Summarize:
   - Completed tasks vs total
   - Current blockers (if any)
   - Last log entry date (if log exists)

---

### update
Update an existing nano-spec.

**Usage**: `/nano-spec update my-task "What to update"`

1. Read existing files in `tasks/$TASK_NAME/`
2. Make requested updates
3. Add entry to log.md with today's date (create log.md if it doesn't exist and the update warrants it)
