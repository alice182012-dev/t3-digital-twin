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

## No separate plan files

There is no `claude-plan/` folder (retired 2026-10-10, `D-025`). A story is the one home of its plan: its
acceptance check, its status history, and its details. Multi-day work with no story gets a story, or a spike
when the answer is unknown. A plan that turns into standing reference of how a subsystem works becomes a concept
page. Old plans are in `artifacts/archive/plans/`.

## Scrum: sprints, epics, and stories

Adopted 2026-10-10 (`D-024` in `artifacts/docs/decisions/decision-log.md`). The full process, with the
events and the Definition of done, is in `artifacts/docs/concepts/scrum-framework.md`. This section holds
the rules that every session follows. The sources are Atlassian's Scrum guides, kept in
`artifacts/docs/concepts/project-management/`.

1. **Roles.** The user is the product owner. They order the backlog, write the sprint goal, and accept or
   reject each `Done`. Claude sessions are the development team. Claude also does the duties of a Scrum master:
   keep the events on time and raise impediments as blocker pages.
2. **Sprint.** A sprint is two weeks, Monday of week 1 to Sunday of week 2, and the next sprint starts the next
   Monday. Its dates and number never change after it starts. Sprint planning is on the first Monday and takes
   4 hours at most. A refinement of the backlog is in the middle of the sprint. The review (1 hour) and the
   retrospective (30 minutes) are on the last Sunday. The calendar sets the dates only. Points set how much work
   enters the sprint (rule 3).
3. **One sprint at a time, sized in points.** A story gets a `sprint` number only at sprint planning, for the
   sprint that is being planned. Planning picks `Ready` stories from the top of the backlog until their
   `estimate` points reach the forecast from [[Velocity]]. Weeks do not decide how many stories enter. Never assign a story to a future sprint. A story with `sprint` empty and a status other than
   `Done` or `Superseded` is in the product backlog, ordered by `priority`. Ask the product owner when the
   pick is unclear, and do not guess.
4. **Files.** A story is `docs/stories/US-nnn-<slug>.md`, from `templates/user-story.md`. An epic is
   `docs/epics/EP-nn-<slug>.md`, from `templates/epic.md`, and it holds the goal, the reason, the assumptions,
   and the definition of done that a PRD held. A sprint is `docs/sprints/SPR-nnn-<slug>.md`, from
   `templates/sprint.md`, where nnn is the sprint number. PRDs and four-sprint plans are retired and live in
   `archive/`. The hierarchy is theme, then epic, then story. Keep epics few.
5. **Story fields.** A story has `us_id`, `title`, `epic`, `kind` (`story`, `spike`, or `bug`), `status`,
   `priority`, `estimate` (XS=1, S=2, M=3, L=5 points), and `sprint`. Statuses are `Not started` (in the
   backlog), `Ready`, `In progress`, `Reviewed`, `Blocked`, `Done`, and `Superseded`.
   **Definition of ready.** A story is `Ready`, and so may enter a sprint, only when it passes the INVEST
   check: independent (its dependencies are done or in the same sprint), negotiable, valuable (the user value or
   the question is stated), estimable (it has an estimate), small (not rated L, so it fits one sprint), and
   testable (the acceptance check names the environment). Planning takes only `Ready` stories.
6. **Spikes.** An experiment or a proof is a story with `kind: spike`, a question, and a timebox of one sprint
   or less. It ends with an answer in the story and a `D-nnn` decision. It does not need a UI screenshot. An
   idea in `raw/ideas/` stays read-only. The spike links it in `source_ideas` and works in `marie-curie/`.
7. **Definition of done.** A story reaches `Done` only when the acceptance check passes in the environment it
   names, tests pass, the concept page it changes is updated with `last_updated` bumped, and the story file
   holds evidence and a numbered details list. Evidence is a screenshot under
   `artifacts/docs/stories/evidence/`, embedded with `![[name.png]]`. A UI story gets a screenshot of the
   running UI. A backend story with no UI gets a screenshot of the real output, with a caption that gives
   the capture time and host. When the acceptance check says server, a screenshot from a laptop does not
   count. A spike records its measured result instead. Take the screenshot before changing the status. If the
   check fails, log the failure as a blocker and leave the story off `Done`. A story that is not `Done` at the
   review leaves the sprint: clear `sprint` and estimate it again.
8. **Work in progress.** At most two stories are `In progress` at once. A story that waits on a long run or on
   an outside event starts that wait first. A story that waits on something that may not happen this sprint
   (real rain, for example) does not enter the sprint.
   **Mid-sprint work.** A new fix, feature, or bug found during a sprint is written as a story in the backlog,
   with `sprint` empty. It enters the sprint only if it threatens the sprint goal, and the product owner
   decides what leaves. The sprint goal does not change.
9. **`TODOS.md`** shows the current sprint and holds no state of its own. Never add an item by hand. Set the
   story's `sprint` at planning, and the query shows it.
10. **Review and retrospective.** On the last day, fill the Review and Retrospective sections of the sprint
    file: the goal met or not, the points delivered, the stories that left, then what worked, what did not, and
    one action. Check the previous action first. An action becomes a story, a rule change, or an `L-nnn`
    lesson. Record the actual dates only in the sprint file's frontmatter, since a sprint's dates do not move.
11. **Velocity.** `artifacts/Velocity.md` sums the points of `Done` stories by sprint. Plan a sprint from the
    last three values. The forecast is in points per sprint, not weeks or hours per person.
12. **A blocker is an impediment.** A blocker found in a sprint gets a blocker page the same day, from
    `templates/blocker.md`. Say on the page whether it blocks the sprint goal, and why. If it does, fix it
    first and put it first in the daily log. If it does not, it waits for planning, or a subagent in its own
    worktree fixes it while the sprint continues. Review the subagent's diff before it lands.
13. **IDs.** Every document has one code at the start of its file name: `US-nnn` (story), `EP-nn` (epic),
    `SPR-nnn` (sprint, equal to the sprint number), `BL-nnn` (blocker), `L-nnn` (lesson), and `D-nnn`
    (decision). A code is assigned once from the next free number in the Conventions of `artifacts/Home.md`,
    never reused, and never renumbered. A story keeps its ID when it changes sprint, and the parts of a split
    story get new IDs. Take the number before writing the file, and raise the next free number in `Home.md`.
    Link a renamed document with its full file name and a short alias.

The rules of the old four-sprint plan (numbered 1 to 12 before 2026-10-10) are retired. Old stories and
blockers that cite "rule 8" or "rule 11" mean those rules and stay as written.

## Verification discipline for epics and cross-referencing documents

Rules learned from mistakes made while drafting this project's PRDs, epics, and user stories. The PRD rules now apply to the epic file, which took over the PRD's sections. Each links
to its full incident under `artifacts/docs/lessons/`; the lesson page holds the "why", this list is
the checkable rule to apply going forward.

- Before ruling a data store out as a source for something, read the code that writes into it, not
  just a schema summary or the query that happens to read it today. See
  [[lessons#L-009|L-009]].
- Record a user's short stated answer as a decision (in an epic or the decision log) only after checking it actually resolves
  the question that was asked, not by transcribing it as-is. See
  [[lessons#L-008|L-008]].
- When an epic's Goal changes scope, re-read Why, Dependencies and
  assumptions, Definition of done, and Risks for sentences that assumed the old scope. See
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
other file links to it. This applies to the vault below and to the Scrum rules above.

| Fact | Its one home |
| --- | --- |
| A story's status, evidence, numbers, and details | the story file (Status history, Evidence and details) |
| A decision and its reason | `artifacts/docs/decisions/decision-log.md` |
| A blocker's state and attempts | the blocker page |
| What a subsystem is and how it works | the concept page |
| The sprint of a story | the story's `sprint` field, read by queries |
| A sprint's goal, review, and retrospective | the sprint file |
| An epic's goal and definition of done | the epic file |
| A day's server facts, commands, and pickup list | that day's log |

1. A story moving to `Done`, `Reviewed`, or `Blocked` is written in its story file only. The Status history of an
   epic or a sprint file records plan-level changes only: a story added, split, moved to another epic, or
   dropped, a sprint started or finished, and the blocker case of rule 12. The Dataview queries show the rest.
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
`artifacts/Home.md` for the index and conventions. The product backlog is the set of
story files with no sprint. `artifacts/TODOS.md` shows the current sprint by query. Several kinds of files live here, and each has a different
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
- **Logs** (`artifacts/logs/`) are the daily scrum: what happened, in the order
  it happened. Append-only, one file per working day. Never rewritten after the
  fact except to add a `related` link. A daily log is an index (see "Write each
  fact once") of about 20 lines: a summary of the previous day (a standing rule
  from the user), what moved, what moves next, what blocks, and server facts that
  have no other home. One line per event, linking to the story, blocker, or
  decision that holds the detail. It holds no pickup list, because the sprint
  file and the backlog do.
- **Archive** (`artifacts/archive/`) holds retired documents: logs before 2026-10-01, finished plans, resolved
  blockers, the story-level history lines of epics and sprint plans, and the research cut from long pages. It is
  excluded from Obsidian search (`userIgnoreFilters`), no Dataview query reads it, and sessions do not open it
  unless a link leads there. Wikilinks to an archived file still resolve by name. Move a file there with
  `git mv` when its story or plan is `Done` and nothing reads it daily.
- **Concept pages** (`artifacts/docs/concepts/`) are the standing reference,
  one page per subsystem (for example `graphhopper-backend.md`,
  `minio-flood-extent-pipeline.md`): what it is, how it works now, and its
  open items, cited against real file paths and line-level facts, not
  paraphrased from memory. A story that changes something a concept page
  describes updates that page before it is `Done` (Definition of done, item 3),
  and bumps `last_updated`. A log records that something happened; a concept page
  is where a later session goes to learn the subsystem without re-reading every
  log that ever touched it.
- Before writing a new concept page, check whether one already exists for
  that subsystem (`artifacts/docs/concepts/`, or `artifacts/Home.md`'s
  Concepts query) and update it instead of starting a new one.
- **Blocker pages** (`artifacts/docs/blockers/`) are the deep record for one
  blocker. Start a new one from `artifacts/templates/blocker.md`. It holds
  Description, Why this matters, one `### Approach N` subsection per attempt,
  Decision and explanation, and optionally Concerns; a concept page or
  story links to the blocker page for this detail instead of
  repeating it, and the story gets a `**Blocker tracking:**` line
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
decision into `artifacts/docs/decisions/decision-log.md` or `artifacts/docs/concepts/`)
instead of leaving finished work sitting in scratch space.

`marie-curie/` also pairs with `artifacts/raw/ideas/`: an idea written down
there is what to try, `marie-curie/` is where the trying happens. Check
`artifacts/raw/ideas/` for a matching idea note before starting an
experiment from scratch, and when the experiment concludes (whether it
worked or not), that's worth a line in the day's log even if nothing in
`marie-curie/` itself survives.
