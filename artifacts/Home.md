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
the blocker's state changes, unlike a log entry, which is never rewritten. The story
tracks the work item (effort, priority) and links to the blocker page for the deep record, not the other way
around.

For the status, priority, approach counts, and dates of every blocker, see [[Blockers board]].

## Current sprint

See [[TODOS]]. A script generates it from the story, sprint, and blocker frontmatter, so it reads in the terminal, where Dataview does not run. Run `python3 -I scripts/render_todos.py` after you change a story. Only its Next action block is hand-written.

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

## Product backlog

Every story with no sprint and a status other than `Done` or `Superseded`, ordered by priority. The sprint planning picks from the top. See [[scrum-framework]] for the process.

```dataview
TABLE title AS "Story", kind AS "Kind", priority AS "Priority", estimate AS "Estimate", status AS "Status", epic AS "Epic"
FROM "docs/stories"
WHERE type = "user-story" AND !sprint AND status != "Done" AND status != "Superseded"
SORT priority ASC, file.name ASC
```

For every story, see [[User stories board]]. For points done per sprint, see [[Velocity]].

## Sprints

One file per sprint in `docs/sprints/`, named `SPR-nnn-<slug>.md`. A sprint is two weeks, Monday to the Sunday of the next week. Story points, not weeks, decide how many stories enter. The file holds the goal, the dates, the review, and the retrospective. Its story list is a query on `sprint`. Start one from `templates/sprint.md`.

```dataview
TABLE sprint AS "Sprint", start_date AS "Start", end_date AS "End", status AS "Status"
FROM "docs/sprints"
SORT sprint DESC
```

## Epics

A body of work of several weeks, with its goal, reason, assumptions, and definition of done. Start one from `templates/epic.md`. Its stories are listed by query inside the file.

```dataview
TABLE theme AS "Theme", status AS "Status", subsystem AS "Subsystem"
FROM "docs/epics"
SORT file.name ASC
```

## Lessons learned

Short, checkable rules distilled from resolved blockers, one section per lesson in `docs/lessons/lessons.md`. Add a new `## L-nnn` section when closing a blocker whose cause would generalize to other subsystems. A section links to the archived original for the full incident.

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
- Every log, plan, decision, concept, blocker, lesson, idea, epic, sprint, and user story doc gets a YAML
  frontmatter block: `date` (`date_open` for a blocker, `date_drafted` for an epic or user story, `date_captured`
  for a lesson or idea), `type` (`log`/`decision`/`concept`/`blocker`/`lesson`/`idea`/
  `user-story`/`epic`/`sprint`/`reference`), `status` (`active`/`parked`/`done`/`superseded` for most;
  `open`/`monitoring`/`resolved`/`wont-fix` for a blocker; `Not started`/`Ready`/`In progress`/`Reviewed`/`Blocked`/`Done`/`Superseded` for a user story, `active`/`done`/`parked` for an epic, `planning`/`active`/`done` for a sprint;
  `active`/`retired` for a lesson; `unexplored`/`exploring`/`go`/`needs-clarification`/`killed` for
  an idea), `tags`, and `related` (a list of `[[wikilinks]]` to what it's tied to).
- `artifacts/archive/` holds retired documents (old logs, retired plans, resolved blockers, story-level history, cut research). It is excluded from Obsidian search and from every query here. Wikilinks to archived files still resolve by name.
- Every document kind has a code, and the code starts the file name, so a search for the code finds the file. The codes are `US-nnn` (user story, `docs/stories/`), `EP-nn` (epic, `docs/epics/`), `SPR-nnn` (sprint, `docs/sprints/`, equal to the sprint number), `BL-nnn` (blocker, `docs/blockers/`), `L-nnn` (lesson, `docs/lessons/`), and `D-nnn` (decision, in `decision-log.md`). A code is assigned once from the next free number below, never reused, and never renumbered. Link a document by its full file name with the old or short name as an alias: `[[BL-023-9c-sampling-step-runs-over-770-seconds|9c sampling step]]`. Concept pages, logs, and plans keep topic or date names. The retired codes `PRD-nnn` and `SP-nn` stay in `archive/`. The next free numbers are `US-115`, `EP-22`, `SPR-014`, `BL-029`, `L-013`, and `D-035`. Raise the number when you assign one.
- A user story (`docs/stories/US-nnn-<slug>.md`) is work that fits one sprint. Its frontmatter holds `us_id`, `title`, `epic`, `kind`, `status`, `priority`, `estimate`, and `sprint`, and the file holds the story text, its evidence, and its numbered details. Nothing else keeps a second copy of those fields: the sprint file, the boards, the epic, and `TODOS.md` read them (`TODOS.md` through the script). `sprint` is set only at sprint planning, and moving a story out of a sprint is one edit that clears it. An epic file holds the goal, reason, assumptions, and definition of done, and lists its stories by query. A sprint file never lists stories by hand. See [[scrum-framework]] and `.claude/CLAUDE.md`, "Scrum: sprints, epics, and stories", for the full convention.
- A lesson (a `## L-nnn` section of `docs/lessons/lessons.md`) is a short, checkable rule distilled from a resolved blocker, not a
  retelling of the incident. Write one when closing a blocker whose cause would generalize past
  the one subsystem it happened in, and link the source blocker in `source_blockers` instead of
  copying its approach history.
- A blocker page (`docs/blockers/`) is the deep record for one blocker: description, why it
  matters, one subsection per approach tried, and the eventual decision. It is the one place this
  detail lives; a concept page or story links to the blocker page rather than repeating
  the approach-by-approach narrative. Edit `status`, `date_closed`, `approaches_tried`, and
  `approaches_remaining` in place as the blocker's state changes, and add a dated bullet to its
  "Status history" section on every status change or new attempt, including a failed one.
- A concept page (`docs/concepts/`) is the standing reference for one subsystem: what it is, how
  it works, and its open items, cited against real file paths. A story that changes
  something a concept page describes updates that page before it is `Done`. `last_updated` tracks the date of the last such pass, separate from
  `date` (when the page was created).
- `TODOS.md` is generated by `scripts/render_todos.py` and holds no state of its own, except the hand-written Next action block. The sprint file holds the goal, the dates, the review, and the retrospective.
- A file name has none of the characters `? : * " < > |` and does not end in a dot or a space, because the server is Windows and `git pull` refuses such a path. Web clippings often carry a `?`, so rename them before you commit.
- Screenshots referenced from a log go under `logs/image/<date>/`; create the folder when the
  first screenshot for that date is added, don't pre-create empty ones.
- New logs, sprints, epics, and stories should start from the templates in `templates/` (Templater) so the
  frontmatter and section structure stay consistent.
