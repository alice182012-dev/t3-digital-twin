## gstack (REQUIRED, global install)

The hook `.claude/hooks/check-gstack.sh` (registered in `.claude/settings.json`) blocks skill use when gstack
is missing and prints the install steps. If it blocks, stop and tell the user to install it
(`git clone --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack`, then
`cd ~/.claude/skills/gstack && ./setup --team`, then restart). Do not skip skills, ignore gstack errors, or work
around a missing gstack. Use `/browse` for all web browsing (Aside first, the bundled gstack browser as
fallback). gstack file paths use the install path, by default `~/.claude/skills/gstack`.

## Docker: check which machine you're on before touching it

This project's Docker host is the Windows machine at `100.67.84.55`
(user `TECOTEC`). A Claude Code session on this project runs in one of two
places, and the right `docker`/`docker compose` invocation is different in
each:

- **On the Mac**, the Docker host is remote. A `docker context ls` there
  shows a `remote-server` context pointing at `ssh://tecotec@100.67.84.55`.
- **Directly on the `TECOTEC` Windows machine itself** (`100.67.84.55`), the
  Docker host is the local machine. There is no SSH hop, and no
  `remote-server` context exists at all — `docker context ls` there shows
  only `default` and `desktop-linux`.

**Check which case you're in before running any docker command.** The
cheapest check is `docker context ls`: if a `remote-server` context exists,
you're on the Mac and need it; if it doesn't exist, you're already running
on the server, so there is nothing remote to reach. (`hostname` and the
machine's IP confirm the same thing: `ADMIN`/`100.67.84.55` is the server
itself.)

**Case 1 — running on the Mac:**

1. Check the active context: `docker context ls` (the current one is
   marked `*`). If it isn't `remote-server`, scope the command with
   `--context remote-server` (for example
   `docker --context remote-server compose up -d`) rather than switching
   the context globally with `docker context use remote-server` — that
   command changes state for every other shell and project on this
   machine, not just this one, so prefer the per-command flag unless the
   user asks to switch it for the session.
2. Local edits are invisible to the remote host until they're pushed and
   pulled there. `compose.yml`'s services bind-mount host paths
   (`./dags`, `./scripts`, `./data`, and so on), and those paths resolve
   on the **remote** host's filesystem when the active context is
   `remote-server`, not on this machine's. Before `docker compose up`,
   `build`, or `restart` is expected to pick up a local change, get it
   onto the server first:
   ```bash
   ssh tecotec@100.67.84.55 "cd C:\Users\TECOTEC\airflow_new && git pull"
   ```
   The remote host is Windows; that `cd` runs in its default shell
   (cmd.exe over OpenSSH), not bash, so don't rewrite the path to a
   forward-slash or WSL-style form.
3. Then run the compose command against the remote context, for example
   `docker --context remote-server compose up -d` or
   `docker --context remote-server compose logs -f`.

Never assume a local `docker compose up` on the Mac reflects what's actually
running; the local Docker daemon on the Mac is not the one this project's
containers run on.

**Case 2 — running directly on the `TECOTEC` Windows server:** the working
directory already is the live one, so skip all of the above. Run
`docker`/`docker compose` commands directly, with no `--context
remote-server` flag (that context doesn't exist here and the flag would just
error) and no SSH or `git pull` step. Whatever branch is checked out in this
working directory is what the containers will build and mount.

## Push to the remote that points at `alice182012-dev/t3-digital-twin`

This project's GitHub repo is `github.com/alice182012-dev/t3-digital-twin`. Run
`git remote -v` before the first push or pull in a session and use the remote whose URL is that
repo. As of 2026-10-05 it is `origin`, on the Mac checkout and in the cloud session. An older
checkout may still have `origin` pointing at `github.com/3plus1wheels/airflow_new.git`, which the
authenticated git user cannot push to (a 403 that lands the work nowhere), with the real repo as a
second remote named `alice`. In that case use `alice`, for example `git push alice <branch>`.

Name the remote in every command (`git push origin <branch>`, `git fetch origin <branch>`) so a
changed remote list cannot send the push somewhere else.

## Test points stay inside the model border

The 3Di flood model covers a rectangle of Hanoi. Every test that uses a
coordinate must use one inside it: a depth lookup, a place popup, a route, a
demo, or an evidence screenshot. Outside the border the raster has no depth
values and GraphHopper often finds no road, so the test fails for a reason
that has nothing to do with the change under test.

The border, in EPSG:4326:

- Longitude 105.7015 to 105.7971.
- Latitude 20.9754 to 21.0269.

The numbers are the extent of `flood_depth_raster_tile`. All 8 retained runs on
2026-09-29 had the same extent. Check a point before you use it. Write the
pair as latitude first when you type it into the frontend, and as
longitude first in an API body.

Do not use the `bbox` from GraphHopper's `/info` as the border. It is
105.665404, 20.887149, 105.901313, 21.127032, and it contains central Hanoi,
where a route fails with `Cannot find point`.

Points outside the border, which fail or give no depth:

- 21.0285, 105.8542 (Hoàn Kiếm) is outside on both axes.
- 21.0300, 105.7620 is outside the north edge by about 340 m.

A route pair inside the border that the frontend routed with the truck profile
on 2026-09-29 at 18:15 UTC:

- 21.0250, 105.7550 to 21.0255, 105.7620, 1.9 km and 3 min.

A point inside the border can still give no route, because the flood changes
from run to run. On the same day, 21.0090, 105.7340 started inside deep water
and the frontend showed an error for the truck profile, and 21.0215, 105.7610
to 21.0230, 105.7650 showed "No safe route available". Pick a pair, run it once
in the frontend, and keep it only if it routes.

Read the border again when the 3Di model or its grid changes, and update the
numbers here. A read-only check on the server:

```bash
docker --context remote-server exec airflow_new-storage-postgres-1 psql -U minio_custom -d minio_custom -At -c "select ST_Extent(rast::geometry) from flood_depth_raster_tile"
```

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

Key routing rules:
- Product ideas/brainstorming → invoke /office-hours
- Strategy/scope → invoke /plan-ceo-review
- Architecture → invoke /plan-eng-review
- Design system/plan review → invoke /design-consultation or /plan-design-review
- Full review pipeline → invoke /autoplan
- Bugs/errors → invoke /investigate
- QA/testing site behavior → invoke /qa or /qa-only
- Code review/diff check → invoke /review
- Visual polish → invoke /design-review
- Ship/deploy/PR → invoke /ship or /land-and-deploy
- Save progress → invoke /context-save
- Resume context → invoke /context-restore
- Author a backlog-ready spec/issue → invoke /spec

## Combined gstack + pstack workflow

gstack owns the lifecycle (idea → shipped); pstack owns how code gets written
within that lifecycle. Stage-by-stage:

1. **Ideation/scope** — gstack: `/office-hours` for brainstorming, `/plan-ceo-review`
   for scope decisions.
2. **Architecture** — overlap point, pick by altitude. `/plan-eng-review` (gstack)
   for "is this the right system-level approach" (eng-manager persona review);
   `pstack:architect` for the actual types/module-boundary design once the approach
   is committed. Run eng-review first, then architect on the approach it approved.
3. **Implementation** — pstack owns this (the global instructions require it before any code). Enter via
   `pstack:poteto-mode` for anything non-trivial; it routes to `pstack:tdd`
   (bug w/ repro), `pstack:how`/`pstack:why` (understanding existing code) as needed.
4. **Review** — two different jobs. `pstack:interrogate` (multi-model diff review,
   fast, local) as first pass before gstack's `/review` (fuller review pipeline,
   pre-ship gate) or `/design-review` if UI is touched.
5. **QA** — gstack `/qa` or `/qa-only`. No pstack equivalent.
6. **Ship** — gstack `/ship` or `/land-and-deploy`, then `/canary` if the deploy
   is worth watching.

Where both stacks offer something (architecture, review), default to gstack's
version when the concern is business/product altitude ("is this the right
thing to build/safe to ship") and pstack's when it's engineering altitude
("is this code well-structured").

## Plans live in artifacts/docs/claude-plan

Write a plan file in `artifacts/docs/claude-plan/` only for multi-day work that has no story file, and name it
after what is being built (for example `flood-extent-polygon-tiles-airflow-minio.md`). Work that has a story
file keeps its plan in that story: its acceptance check, its status history, and its details. A story is the
one home of its plan (see "Write each fact once"). Update a plan file as the plan changes, and read the
matching plan first when resuming that topic. When the work is done, set the plan's `status` to `done` and move
it to `artifacts/archive/plans/`, so sessions stop reading it.

## User stories and sprint planning

Once a PRD's goals are settled, break it into user stories, one file per story under
`artifacts/docs/stories/` (`US-nnn-<slug>.md`), following `artifacts/templates/user-story.md` and
`artifacts/docs/templates/user-story-types.md` for shape selection (Simple,
Epic, Thematic, SAFe).

1. Default to the Epic shape for a PRD-derived feature area: one epic file
   under `artifacts/docs/epics/` (`EP-nn-<slug>.md`) that links to its stories,
   and one story file per story, each still a story you could pull out and
   start on its own.
2. Every story file carries `priority`, `estimate`, `sprint`, `status`, and `epic`
   in its frontmatter. This is a deliberate extension on top of
   `user-story-types.md`'s documented shapes, which have no per-story scheduling
   field outside Thematic. The story file is the only place these values are
   recorded. Leave `sprint` empty for a story still in the backlog.
3. A sprint plan has four sprints (rule 10). Real dependencies decide which of
   the four a story lands in, not how many sprints there are. Read each source
   PRD's Dependencies and assumptions and Definition of done sections, and let
   a story that reads another story's output land in a later sprint than the one
   that produces it. A story with no unresolved dependency can go in the
   earliest sprint that has room.
4. A story whose PRD marks its data source or design as an open risk (its
   Risks and open questions section) gets no sprint number and stays in a
   backlog table instead, cross-linked to the blocking risk. Scheduling a
   blocked story just to fill a sprint hides its real state.
5. Write one sprint-plan file per planning pass under
   `artifacts/docs/sprints/`, holding the goal and dates of each sprint, a "why
   these four sprints" explanation, and a Risks table. Each sprint section lists
   its stories with a Dataview query over the story frontmatter
   (`WHERE sprint = N`), never by hand. Update the plan, don't replace it, when
   stories are added to the sprint it already covers. Start a new planning pass
   (new sprints, not an addition to the current one) as a new file instead:
   `SP-nn-<slug>.md` with `plan_number: nn`, so multiple plans can coexist as a
   dated record instead of overwriting one another.
6. Invoke the `product-management:sprint-planning` skill for the planning
   methodology (capacity framing, sprint goal, risk table shape) when
   creating or revising a sprint plan. This project has no connected team
   roster or calendar, so capacity stays qualitative (relative estimate,
   dependency order), not tracked hours or points per person, until real
   velocity data exists.
7. A user story's `related` frontmatter links back to its epic and its source
   PRD. A sprint plan's own `related` links every epic file it schedules.
8. A story reaches `Done` only with evidence and details, recorded in its story
   file under "Evidence and details". The sprint plan shows the status through its
   query, so nothing else is edited. A story without both stays
   `Reviewed` (built and read through, acceptance check not yet passed) or
   `Blocked`.
   - **Evidence** is a screenshot of that story working, saved under
     `artifacts/docs/stories/evidence/` and embedded with `![[name.png]]`.
     A UI story gets a screenshot of the running UI. A backend story with no
     UI gets a screenshot of the real output: the endpoint's response in a
     browser, or the verbatim command output rendered to an image whose
     caption says it is rendered output and gives the capture time and host.
     Capture it in the environment the acceptance criteria name. When they say
     server, a screenshot from a laptop does not count.
   - **Details** are a numbered list of a few plain sentences: 1. what was
     built, 2. how, 3. why, 4. what it changes for dependent stories or open
     blockers, and more numbered points if needed. Write it as a real numbered
     list in the story file.
   - Take the screenshot before changing the status. If the check fails, log
     the failure as a blocker and leave the story off `Done`.
9. `TODOS.md` follows the sprint plan strictly. Any new fix or feature, including
   one that comes up mid-task, is first written as a story and given a sprint in
   the current sprint plan (or in a new plan if it starts a new pass), by setting
   `sprint` in its story file. Only after that does it appear in `TODOS.md`,
   and its item carries a `**Sprint:**` line linking to the plan. Never add a
   `TODOS.md` item directly, and never leave a story unscheduled without a
   Status history entry that says what blocks it (see rule 4). A bug found while
   working goes to a blocker page and a story with a sprint first, and `TODOS.md`
   second. Ask which sprint if the right one is unclear, instead of guessing.
   `TODOS.md` follows the template the user set on 2026-09-30, with no extra
   text. It has three sections: the current sprint, a "Backlog" (the unfinished
   items carried over from the sprint before), and "Blockers for the next
   sprint". Items of later sprints stay in the sprint plans. Each story is a
   heading `### <Status> - US-nnn <title>` (Active or Done), with no `Status::`
   line and no item numbers. The current-sprint heading runs from the
   sprint's actual start date to its planned end date. When an item finishes, change the status in its
   heading in the same pass that moves its story to `Done`, and add a one-line
   result. Done items stay until the next day's rollover, then they are deleted.
   When a sprint ends, move its unfinished items to the Backlog.
10. A sprint is one week, and a sprint plan covers four sprints, so four weeks.
   Every story in a plan lands in one of those four sprints. Work that does not
   fit in the four weeks goes to the next plan (`SP-nn-<slug>.md`, whose sprint
   numbers continue where the last plan stopped) or, if a risk blocks it, to a
   backlog table with the blocking reason (rule 4). Never add a fifth sprint to a
   plan. Size each sprint to what fits in one week, by relative estimate until
   real velocity exists (rule 6). When a sprint looks too full, move rows to a
   later sprint or the next plan and record the move in the plan's Status
   history. Ask before moving a row the user placed.
   Every plan records `start_date` and `end_date` in its frontmatter, starts on
   a Monday, and gives each sprint a `**Dates:**` line (`YYYY-MM-DD to
   YYYY-MM-DD`, Monday to Sunday). The next plan starts on the Monday after the
   last sprint ends, so sprint dates never overlap or leave a gap.
   When a sprint starts or finishes, record its actual date in the timeline table
   of its sprint plan (the "Actual start" and "Actual end" columns) and add a
   Status history line. The planned "Start" and "End" columns do not change.
11. A blocker found in a sprint is settled before a new sprint starts, by whether
   it blocks further build:
   - If it blocks build in the next sprint, fix it first. Do not touch a story of
     the next sprint until the blocker is `resolved`.
   - If it does not block further build, spin a subagent to fix it and continue
     with the next sprint in the meantime. Give the subagent its own worktree and
     a brief that points to the blocker page. Review its diff before it lands.
   Say which case a blocker is, and why, on the blocker page and in the sprint
   plan's Status history, when it is logged. A blocker in a sprint that is
   unscheduled or not yet started stays with rule 9 (ask which sprint).
12. Every user story has one global ID, `US-nnn`, assigned once from the next free
   number in the Conventions of `artifacts/Home.md`, and never reused or renumbered.
   The ID starts the story's file name (`US-094-archive-results-3di-nc-and-a-run.md`),
   is the `us_id` in its frontmatter, and heads its `TODOS.md` item. A story keeps
   its ID when it changes sprint, and the parts of a split story get new IDs. Take
   the number before writing the story, and raise the next free number in `Home.md`.
   The other document kinds are coded the same way: `EP-nn`, `SP-nn`, `PRD-nnn`,
   `BL-nnn`, and `L-nnn`, each at the start of its file name, with the next free
   number in `Home.md`. Link a renamed document with its full file name and a short
   alias.

## Verification discipline for PRDs and cross-referencing documents

Rules learned from mistakes made while drafting this project's PRDs and user stories. Each links
to its full incident under `artifacts/docs/lessons/`; the lesson page holds the "why", this list is
the checkable rule to apply going forward.

- Before ruling a data store out as a source for something, read the code that writes into it, not
  just a schema summary or the query that happens to read it today. See
  [[lessons#L-009|L-009]].
- Record a user's short stated answer as a PRD Decision only after checking it actually resolves
  the question that was asked, not by transcribing it as-is. See
  [[lessons#L-008|L-008]].
- When a PRD's Goals section changes scope, re-read Problem, Non-goals, Dependencies and
  assumptions, Definition of done, and Rollback for sentences that assumed the old scope. See
  [[lessons#L-005|L-005]].
- After editing a document, grep the vault for `[[wikilinks]]` to it and check whether every
  document that cross-references it still holds true. See
  [[lessons#L-001|L-001]].
- Put "invoke `pstack:technical-writing` and `pstack:unslop` before writing" inside a subagent's
  own instructions when it's drafting a technical document, not just in a review pass afterward.
  See [[lessons#L-004|L-004]].
- Test locale- or region-scoped behavior with a real target-language query (with its actual
  diacritics or script, chosen to be ambiguous with a same-name place elsewhere), not an
  English-only placeholder. See [[lessons#L-007|L-007]].
- When a shared convention file changes mid-session, recheck files already created earlier in the
  session against the new rule, not only files created after noticing the change. See
  [[lessons#L-006|L-006]].

## Write each fact once

Added 2026-10-10 after a day in which one decision was copied into six files. A fact has one home, and every
other file links to it. This applies to the vault below and to rules 8, 9, and 10 above.

| Fact | Its one home |
| --- | --- |
| A story's status, evidence, numbers, and details | the story file (Status history, Evidence and details) |
| A decision and its reason | `artifacts/docs/decisions/decision-log.md` |
| A blocker's state and attempts | the blocker page |
| What a subsystem is and how it works | the concept page |
| The sprint of a story | the story's `sprint` field, read by queries |
| A day's server facts, commands, and pickup list | that day's log |

1. A story moving to `Done`, `Reviewed`, or `Blocked` is written in its story file only. The Status history of an
   epic or a sprint plan records plan-level changes only: a story added, moved to another sprint, split, or
   dropped, a sprint started or finished, and the blocker case of rule 11. The Dataview queries show the rest.
2. A daily log is an index. Write one line per event with a link to the file that holds the detail. Do not
   copy numbers, tables, or details that a story, blocker, or decision already holds. Keep in the log only what
   has no other home.
3. Write the vault once per work block. Finish the work, edit each file once, and make one vault commit. Do not
   commit after each step.
4. Do not put a commit hash in prose. Name a commit by its story ID or the first line of its message. The
   "Evidence and details" of one story may hold a hash. A hash in prose breaks when a history rewrite, such as
   removing an attribution line, changes it, and the fix touches every file that quoted it.

## artifacts/ is an Obsidian vault, maintained as a wiki

`artifacts/` is a working knowledge base, not a folder of one-off notes. See
`artifacts/Home.md` for the index and conventions. The project backlog lives
at `artifacts/TODOS.md`, inside the vault (moved there from the repo root on
2026-09-22 so Obsidian, which cannot see outside its own vault folder, can
actually index it). Five kinds of files live here, and each has a different
maintenance rule:

- **`artifacts/raw/`** is the user's own source material: architecture notes,
  design mockups, ideas, research, anything they drop in directly. It is the
  single source of truth and it is read-only for Claude. **Never create,
  edit, rename, move, or delete a file inside `artifacts/raw/`.** Read from
  it freely to inform plans, logs, and concept pages, but the synthesis goes
  in those folders, never back into `raw/`. If asked to change something in
  `raw/`, confirm that's really what's meant before touching it, since this
  is the one folder in the vault where "just do it" is the wrong default.
  `artifacts/raw/ideas/` is where an idea for experimentation gets written
  down before any code exists for it, and it pairs directly with
  `marie-curie/` (repo root, see its own section below): the idea note says
  what to try, `marie-curie/` is where the trying actually happens. Never put
  experiment code, scripts, or data dumps in `raw/ideas/`; that's what
  `marie-curie/` is for.
- **Logs** (`artifacts/logs/`) and **plans** (`artifacts/docs/claude-plan/`)
  are the primary record: what happened, in the order it happened. Append-only,
  one file per day or per plan. Never rewritten after the fact except to add
  a `related` link or close out a status. A daily log is an index (see "Write
  each fact once"): one line per event, linking to the story, blocker, or
  decision that holds the detail.
- **Archive** (`artifacts/archive/`) holds retired documents: logs before 2026-10-01, finished plans, resolved
  blockers, the story-level history lines of epics and sprint plans, and the research cut from long pages. It is
  excluded from Obsidian search (`userIgnoreFilters`), no Dataview query reads it, and sessions do not open it
  unless a link leads there. Wikilinks to an archived file still resolve by name. Move a file there with
  `git mv` when its story or plan is `Done` and nothing reads it daily.
- **Concept pages** (`artifacts/docs/concepts/`) are the standing reference,
  one page per subsystem (for example `graphhopper-backend.md`,
  `minio-flood-extent-pipeline.md`): what it is, how it works now, and its
  open items, cited against real file paths and line-level facts, not
  paraphrased from memory. **When a log entry or a finished plan changes
  something a concept page describes, update that concept page in the same
  session** instead of leaving the fact only in the log. A log records that
  something happened; a concept page is where a later session goes to learn
  the subsystem without re-reading every log that ever touched it. Bump
  `last_updated` in that page's frontmatter when you do this.
- Before writing a new concept page, check whether one already exists for
  that subsystem (`artifacts/docs/concepts/`, or `artifacts/Home.md`'s
  Concepts query) and update it instead of starting a new one.
- **Blocker pages** (`artifacts/docs/blockers/`) are the deep record for one
  blocker. Start a new one from `artifacts/templates/blocker.md`. It holds
  Description, Why this matters, one `### Approach N` subsection per attempt,
  Decision and explanation, and optionally Concerns; a concept page or
  `TODOS.md` item links to the blocker page for this detail instead of
  repeating it, and the `TODOS.md` item gets a `**Blocker tracking:**` line
  pointing back. `status` (`open`/`monitoring`/`resolved`/`wont-fix`),
  `date_closed`, `approaches_tried`, and `approaches_remaining` get **edited
  in place** as the blocker's state changes, unlike a log entry, which is
  never rewritten. Add a dated bullet to the page's own "Status history"
  section on every status change or new attempt, including a failed one.
  Create a blocker page when something is actively blocking work and its
  state will need checking again later; a one-off issue fixed in the same
  session just goes in that day's log.

All these file kinds get the frontmatter block documented in
`artifacts/Home.md` (`date` or `date_open`, `type`, `status`, `tags`,
`related`), and load
`pstack:technical-writing` + `pstack:unslop` before writing prose into any of
them, per the user's global instructions.

## marie-curie/ is scratch space, the opposite of artifacts/raw/

`marie-curie/` (repo root) holds experimental code, test scripts, data dumps,
and one-off notebooks while a piece of work is still being figured out.
Nothing under it is tracked by git except its own `README.md`, so it can be
deleted at any time without a git operation. Default to putting throwaway
experiments here instead of scattering them into `scripts/`, `test/`, or the
repo root.

This folder is the opposite of `artifacts/raw/`: `raw/` is read-only and
precious, `marie-curie/` is read-write and disposable. Create, edit, and delete
files in `marie-curie/` freely. When an experiment works and becomes real work,
move it to where it belongs (a script into `scripts/`, a DAG into `dags/`, a
decision into `artifacts/docs/claude-plan/` or `artifacts/docs/concepts/`)
instead of leaving finished work sitting in scratch space.

`marie-curie/` also pairs with `artifacts/raw/ideas/`: an idea written down
there is what to try, `marie-curie/` is where the trying happens. Check
`artifacts/raw/ideas/` for a matching idea note before starting an
experiment from scratch, and when the experiment concludes (whether it
worked or not), that's worth a line in the day's log even if nothing in
`marie-curie/` itself survives.
