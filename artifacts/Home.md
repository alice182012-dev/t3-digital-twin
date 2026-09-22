---
type: home
---

# t3-digital-twin knowledge base

Vault root is this `artifacts/` folder. It holds engineering logs, plans, design docs, and the
project backlog (`TODOS.md`) for the flood-mapping digital twin. See
[[SW Architecture]] for the system architecture.

## Raw sources

```dataview
LIST
FROM "raw"
```

`raw/` is the source of truth: the user's own material, dropped in directly. Claude reads from it
but never creates, edits, moves, or deletes anything inside it.

`raw/ideas/` holds ideas for experimentation: short notes on something worth trying, written before
any code exists for it. It pairs with `../einstein/`, the disposable scratch folder at the repo
root: an idea in `raw/ideas/` describes what to try, and the actual experimenting (code, test
scripts, data) happens in `einstein/`, never in `raw/ideas/` itself. If an experiment in
`einstein/` works out, it graduates into a real plan, script, or concept page; the idea note in
`raw/ideas/` stays as the record of where it started.

## Backlog

```dataview
TABLE Priority AS "Priority", Status AS "Status"
FROM "TODOS.md"
```

## Active plans

```dataview
TABLE date AS "Date", branch AS "Branch"
FROM "docs/claude-plan"
WHERE status = "active"
SORT date DESC
```

## Recent logs

```dataview
TABLE date AS "Date", branch AS "Branch", tags AS "Tags"
FROM "logs"
WHERE type = "log"
SORT date DESC
LIMIT 5
```

## Concepts

One standing page per subsystem, updated whenever a log or plan changes something about it,
instead of leaving that fact only in the log that produced it.

```dataview
TABLE status AS "Status", last_updated AS "Last updated"
FROM "docs/concepts"
SORT last_updated DESC
```

## Design docs

```dataview
LIST
FROM "designs"
```

## Conventions

- `raw/` is read-only for Claude. Never write, rename, move, or delete a file inside it, even if
  asked casually in passing; if the user wants something in `raw/` changed, they do it themselves,
  or say so explicitly enough that there's no ambiguity this is what they mean.
- Every log, plan, decision, and concept doc gets a YAML frontmatter block: `date`, `type`
  (`log`/`plan`/`decision`/`concept`), `status` (`active`/`parked`/`done`/`superseded`), `tags`,
  and `related` (a list of `[[wikilinks]]` to the plan, log, or concept page it's tied to).
- A concept page (`docs/concepts/`) is the standing reference for one subsystem: what it is, how
  it works, and its open items, cited against real file paths. When a log or plan changes
  something a concept page describes, update that page in the same pass instead of leaving the
  fact stranded in the log. `last_updated` tracks the date of the last such pass, separate from
  `date` (when the page was created).
- `TODOS.md` items keep their existing prose format; each item gets one inline field line,
  `Status:: active`, so Dataview can query it without restructuring the file.
- Screenshots referenced from a log go under `logs/image/<date>/`; create the folder when the
  first screenshot for that date is added, don't pre-create empty ones.
- New logs and plans should start from the templates in `.templates/` (Templater) so the
  frontmatter and section structure stay consistent.
