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

## Blockers

One page per blocker: description, why it matters, every approach tried, the eventual decision.
Start a new one from `.templates/blocker.md`. Its `status` and `date_closed` get edited in place as
the blocker's state changes, unlike a log entry, which is never rewritten. `TODOS.md` tracks the
work item (effort, priority) and links to the blocker page for the deep record, not the other way
around.

```dataview
TABLE severity AS "Severity", status AS "Status", subsystem AS "Subsystem",
  approaches_tried AS "Tried", approaches_remaining AS "Remaining",
  (date(date_closed) - date(date_open)).days AS "Days open/to close"
FROM "docs/blockers"
SORT status ASC, last_updated DESC
```

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

## PRDs

One page per feature or change big enough to need a stated problem, goals, and a definition of
done before work starts. Start a new one from `.templates/prd.md`. A PRD comes before its
`docs/claude-plan/` entry: the PRD says what and why, the plan says how. Its **Dependencies and
assumptions** section exists because of blockers such as
[[graphhopper-vehicle-profile-rejection]] and [[storage-backend-build-context-missing]], both
caused by a dependency nothing had written down. When a PRD grew out of a note in `raw/ideas/`,
its `source_ideas` frontmatter field links back to that note instead of retyping its argument.

```dataview
TABLE status AS "Status", subsystem AS "Subsystem", date_drafted AS "Drafted"
FROM "docs/prds"
SORT status ASC, date_drafted DESC
```

## Lessons learned

Short, checkable rules distilled from resolved blockers, one page per lesson. Start a new one from
`.templates/lesson-learned.md` when closing a blocker whose cause would generalize to other
subsystems. A lesson links back to its source blocker for the full incident; it doesn't retell the
approach-by-approach history itself.

```dataview
TABLE status AS "Status", subsystem AS "Subsystem", date_captured AS "Captured"
FROM "docs/lessons"
SORT status ASC, date_captured DESC
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
- Every log, plan, decision, concept, blocker, PRD, lesson, and idea doc gets a YAML frontmatter
  block: `date` (`date_open` for a blocker, `date_drafted` for a PRD, `date_captured` for a lesson
  or idea), `type` (`log`/`plan`/`decision`/`concept`/`blocker`/`prd`/`lesson`/`idea`), `status`
  (`active`/`parked`/`done`/`superseded` for most; `open`/`monitoring`/`resolved`/`wont-fix` for a
  blocker; `draft`/`approved`/`in-progress`/`shipped`/`abandoned` for a PRD; `active`/`retired` for
  a lesson; `unexplored`/`exploring`/`go`/`needs-clarification`/`killed` for an idea), `tags`, and
  `related` (a list of `[[wikilinks]]` to what it's tied to).
- A PRD (`docs/prds/`) states the problem, goals, and definition of done for a feature or change
  before its implementation plan (`docs/claude-plan/`) is written. Its **Dependencies and
  assumptions** section states every fact the design relies on that isn't visible from reading the
  code cold, and **Definition of done** states an operational check rather than a proxy like "it
  compiles" or "no errors in the logs".
- A lesson (`docs/lessons/`) is a short, checkable rule distilled from a resolved blocker, not a
  retelling of the incident. Write one when closing a blocker whose cause would generalize past
  the one subsystem it happened in, and link the source blocker in `source_blockers` instead of
  copying its approach history.
- A blocker page (`docs/blockers/`) is the deep record for one blocker: description, why it
  matters, one subsection per approach tried, and the eventual decision. It is the one place this
  detail lives; a concept page or `TODOS.md` item links to the blocker page rather than repeating
  the approach-by-approach narrative. Edit `status`, `date_closed`, `approaches_tried`, and
  `approaches_remaining` in place as the blocker's state changes, and add a dated bullet to its
  "Status history" section on every status change or new attempt, including a failed one.
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
