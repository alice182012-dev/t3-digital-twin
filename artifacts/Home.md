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
[[BL-001-graphhopper-vehicle-profile-rejection|graphhopper-vehicle-profile-rejection]] and [[BL-002-storage-backend-build-context-missing|storage-backend-build-context-missing]], both
caused by a dependency nothing had written down. When a PRD grew out of a note in `raw/ideas/`,
its `source_ideas` frontmatter field links back to that note instead of retyping its argument.

```dataview
TABLE status AS "Status", subsystem AS "Subsystem", date_drafted AS "Drafted"
FROM "docs/prds"
SORT status ASC, date_drafted DESC
```

## User stories

One file per story in `docs/stories/`, named `US-nnn-<slug>.md`. A story file owns its status, priority, estimate, sprint, epic, evidence, and details. An epic (`docs/epics/EP-nn-<slug>.md`) holds the shared intro for a group of stories and links to them. A sprint plan (`docs/sprints/SP-nn-<slug>.md`) holds the goal, the dates, the risks, and the history, and lists its stories with a query over the story frontmatter. Start a story from `templates/user-story.md`; see [[user-story-types]] for which shape fits. A story comes after its PRD's goals are settled. A story with no sprint number is unscheduled, not forgotten: its Status history says what it is blocked on.

```dataview
TABLE title AS "Story", sprint AS "Sprint", priority AS "Priority", status AS "Status"
FROM "docs/stories"
WHERE type = "user-story" AND status != "Done" AND status != "Superseded"
SORT sprint ASC, priority ASC
```

For every story, see [[User stories board]].

## Sprint plans

```dataview
TABLE plan_number AS "Plan", start_date AS "Start", end_date AS "End", status AS "Status"
FROM "docs/sprints"
SORT plan_number ASC
```

## Epics

```dataview
TABLE us_ids AS "Stories", status AS "Status", subsystem AS "Subsystem"
FROM "docs/epics"
SORT file.name ASC
```

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
- Every document kind has a code, and the code starts the file name, so a search for the code finds the file. The codes are `US-nnn` (user story, `docs/stories/`), `EP-nn` (epic, `docs/epics/`), `SP-nn` (sprint plan, `docs/sprints/`, equal to `plan_number`), `PRD-nnn` (`docs/prds/`), `BL-nnn` (blocker, `docs/blockers/`), and `L-nnn` (lesson, `docs/lessons/`). A code is assigned once from the next free number below, never reused, and never renumbered. Link a document by its full file name with the old or short name as an alias: `[[BL-023-9c-sampling-step-runs-over-770-seconds|9c sampling step]]`. Concept pages, logs, and plans keep topic or date names. The next free numbers are `US-101`, `EP-17`, `SP-05`, `PRD-005`, `BL-028`, and `L-012`. Raise the number when you assign one.
- A PRD (`docs/prds/`) states the problem, goals, and definition of done for a feature or change before its implementation plan (`docs/claude-plan/`) is written. Its **Dependencies and assumptions** section states every fact the design relies on that isn't visible from reading the code cold, and **Definition of done** states an operational check rather than a proxy like "it compiles" or "no errors in the logs".
- A user story (`docs/stories/US-nnn-<slug>.md`) breaks an approved PRD goal into sprint-sized work. Its frontmatter holds `us_id`, `title`, `epic`, `status`, `priority`, `estimate`, and `sprint`, and the file holds the story text, its evidence, and its numbered details. Nothing else keeps a second copy of those fields: the sprint plan, the board, and the epic read them with queries. Moving a story to another sprint is one edit to `sprint` in its frontmatter, plus a Status history line in the sprint plans it leaves and joins. An epic file links to its stories, a sprint plan never lists them by hand. Pick a story's shape from [[user-story-types]]. See `.claude/CLAUDE.md`, "User stories and sprint planning", for the full convention.
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
- `TODOS.md` follows the template the user set on 2026-09-30, with no extra text. It has three
  sections: the current sprint, a "Backlog" (the unfinished items carried over from the sprint
  before), and "Blockers for the next sprint". Each story is a heading `### <Status> - US-nnn
  <title>` (Active or Done), with no `Status::` line and no item numbers. The current-sprint heading runs from the sprint's actual start date to its planned end date. When an item finishes,
  change the status in its heading in the same pass that moves its story to `Done`, with a
  one-line result. Done items stay until the next day's rollover, then they are deleted. Items of
  later sprints stay in the sprint plans.
- Screenshots referenced from a log go under `logs/image/<date>/`; create the folder when the
  first screenshot for that date is added, don't pre-create empty ones.
- New logs and plans should start from the templates in `templates/` (Templater) so the
  frontmatter and section structure stay consistent.
