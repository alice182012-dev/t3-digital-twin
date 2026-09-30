---
type: home
---

# t3-digital-twin knowledge base

Vault root is this `artifacts/` folder. It holds engineering logs, plans, design docs, and the
project backlog (`TODOS.md`) for the flood-mapping digital twin. See
[[T3-Digital-Twin_Architecture]] for the system architecture.

## Raw sources

```dataview
LIST
FROM "raw"
```

`raw/` is the source of truth: the user's own material, dropped in directly. Claude reads from it
but never creates, edits, moves, or deletes anything inside it.

`raw/ideas/` holds ideas for experimentation: short notes on something worth trying, written before
any code exists for it. It pairs with `../marie-curie/`, the disposable scratch folder at the repo
root: an idea in `raw/ideas/` describes what to try, and the actual experimenting (code, test
scripts, data) happens in `marie-curie/`, never in `raw/ideas/` itself. If an experiment in
`marie-curie/` works out, it graduates into a real plan, script, or concept page; the idea note in
`raw/ideas/` stays as the record of where it started.

## Blockers

One page per blocker: description, why it matters, every approach tried, the eventual decision.
Start a new one from `templates/blocker.md`. Its `status` and `date_closed` get edited in place as
the blocker's state changes, unlike a log entry, which is never rewritten. `TODOS.md` tracks the
work item (effort, priority) and links to the blocker page for the deep record, not the other way
around.

For the status, priority, approach counts, and dates of every blocker, see [[Blockers board]].

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
done before work starts. Start a new one from `templates/prd.md`. A PRD comes before its
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

## User stories

One page per user story, or per epic grouping several stories, delegated into a sprint once its
dependencies are known. Start a new one from `templates/user-story.md`; see
[[user-story-types]] for which shape (Simple, Epic, Thematic, SAFe) fits. A user story comes after
its PRD's goals are settled: the PRD says what and why, the user story breaks it into sprint-sized
work. An Epic-shaped story's rows carry Priority, Estimate, and Sprint in addition to the shape's
own fields (an extension past what `templates/user-story.md` and [[user-story-types]] show alone;
see `.claude/CLAUDE.md`, "User stories and sprint planning", for why). A story with no sprint number
is unscheduled, not forgotten: its Status history says what it's blocked on.

```dataview
TABLE status AS "Status", subsystem AS "Subsystem", date_drafted AS "Drafted"
FROM "docs/user-stories"
SORT status ASC, date_drafted DESC
```

For one row per story, with sprint, priority, and status, see [[User stories board]].

## Lessons learned

Short, checkable rules distilled from resolved blockers, one page per lesson. Start a new one from
`templates/lesson-learned.md` when closing a blocker whose cause would generalize to other
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
- Every log, plan, decision, concept, blocker, PRD, lesson, idea, and user story doc gets a YAML
  frontmatter block: `date` (`date_open` for a blocker, `date_drafted` for a PRD, `date_captured`
  for a lesson or idea), `type` (`log`/`plan`/`decision`/`concept`/`blocker`/`prd`/`lesson`/`idea`/
  `user-story`/`reference`), `status` (`active`/`parked`/`done`/`superseded` for most;
  `open`/`monitoring`/`resolved`/`wont-fix` for a blocker; `draft`/`approved`/`in-progress`/
  `shipped`/`abandoned` for a PRD; `draft`/`ready`/`in-progress`/`done` for a user story;
  `active`/`retired` for a lesson; `unexplored`/`exploring`/`go`/`needs-clarification`/`killed` for
  an idea), `tags`, and `related` (a list of `[[wikilinks]]` to what it's tied to).
- A PRD (`docs/prds/`) states the problem, goals, and definition of done for a feature or change
  before its implementation plan (`docs/claude-plan/`) is written. Its **Dependencies and
  assumptions** section states every fact the design relies on that isn't visible from reading the
  code cold, and **Definition of done** states an operational check rather than a proxy like "it
  compiles" or "no errors in the logs".
- A user story (`docs/user-stories/`) breaks an approved PRD goal into sprint-sized work; it comes
  after the PRD, not instead of it. Pick its shape from [[user-story-types]]. An Epic file's rows
  are delegated to a sprint (Priority, Estimate, and Sprint per row, an extension past the shape's
  own documented fields) and cross-linked to the sprint plan that assigned them; see
  `.claude/CLAUDE.md`, "User stories and sprint planning", for the full convention.
- Every user story has one ID in the form `US-nnn`, for example `US-014`. The ID is global across
  the vault. It is assigned once and never reused or renumbered. A story keeps its ID when it
  moves to another sprint, and the parts of a split story get new IDs. The ID follows the story's
  label in its file (`Story 4 (US-014)`) and is listed in the file's `us_ids` frontmatter. The
  `Item` column of each sprint table and each matching `TODOS.md` item carry it too. The next free
  ID is `US-060`. Raise this number when you assign one.
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
- `TODOS.md` has two sections only: a daily "Today, YYYY-MM-DD" section and a "Backlog". When an
  item finishes, set its `Status:: done` in the same pass that moves its story to `Done`, with a
  one-line result. It stays in the daily section for the rest of the day. At the next day's
  rollover, done items are deleted, because the logs and the sprint plan already record them, and
  unfinished items move to the Backlog.
- Screenshots referenced from a log go under `logs/image/<date>/`; create the folder when the
  first screenshot for that date is added, don't pre-create empty ones.
- New logs and plans should start from the templates in `templates/` (Templater) so the
  frontmatter and section structure stay consistent.
