## Docker: check which machine you're on first

The Docker host is the Windows machine at `100.67.84.55` (user `TECOTEC`).
Run `docker context ls` before any docker command.

- **A `remote-server` context exists: you are on the Mac.**
  Scope each command with `--context remote-server`. Do not run `docker context use`.
  Compose bind mounts (`./dags`, `./scripts`, `./data`) resolve on the remote host, so push and then pull there before `up`, `build`, or `restart` can see a local change:
  `ssh tecotec@100.67.84.55 "cd C:\Users\TECOTEC\airflow_new && git pull"`
  (cmd.exe over OpenSSH, so keep the backslash path.)
  A local `docker compose up` on the Mac never reflects what runs on the server.
- **No `remote-server` context: you are on the server itself.**
  Run `docker` and `docker compose` directly, with no `--context` flag and no SSH or `git pull`.
  The checked-out branch is what the containers build and mount.

## Git remote

The repo is `github.com/alice182012-dev/t3-digital-twin`.
Run `git remote -v` before the first push or pull and use the remote with that URL (`origin` since 2026-10-05).
An older checkout may point `origin` at `3plus1wheels/airflow_new.git`, which gives a 403.
There, use the remote named `alice`.
Name the remote in every command.

## Test points stay inside the model border

Every test coordinate (depth lookup, popup, route, demo, evidence screenshot) must be inside the 3Di flood model, in EPSG:4326:

- Longitude 105.7015 to 105.7971.
- Latitude 20.9754 to 21.0269.

Outside it the raster has no depth and GraphHopper often finds no road.
Frontend input is latitude first. An API body is longitude first.
Do not use GraphHopper's `/info` bbox as the border. It includes central Hanoi, where routes fail with `Cannot find point`.
Known failures: 21.0285, 105.8542 (Hoàn Kiếm) and 21.0300, 105.7620 (340 m north of the edge).
A pair that routed with the truck profile on 2026-09-29: 21.0250, 105.7550 to 21.0255, 105.7620.
A point inside the border can still give no route because the flood changes per run. Run a pair once in the frontend and keep it only if it routes.
Re-read the border when the 3Di model or grid changes:

```bash
docker --context remote-server exec airflow_new-storage-postgres-1 psql -U minio_custom -d minio_custom -At -c "select ST_Extent(rast::geometry) from flood_depth_raster_tile"
```

## Skill routing

Implementation goes through `pstack:poteto-mode`.
The `mattpocock-skills` plugin supplies the grill, review, and debugging steps below.

1. **Grill first.** Before writing a new feature or a new story, ask the user to run `/grill-with-docs`.
   The skill is user-invoked only, so Claude cannot start it.
   Do not write the story or any code until the session reaches a shared understanding.
   Its two outputs go to the vault homes, not to the skill's default paths:
   - A resolved term goes into the "Language" section at the top of the concept page for its subsystem in `artifacts/docs/concepts/` (decision `D-052`). Do not create `CONTEXT.md`. Until the page exists, the session carries the term.
   - A decision that meets the skill's three ADR tests goes into `artifacts/docs/decisions/decision-log.md` as the next `D-nnn`, never into `docs/adr/`.
2. **Review.** Review a diff with `pstack:interrogate`, then run `mattpocock-skills:code-review` as the pre-ship gate.
   Pass the story file as the spec argument, because the story is the one home of the plan and the skill's issue-tracker lookup does not apply here.
3. **Hard bugs.** For a hard bug or a performance regression, use `mattpocock-skills:diagnosing-bugs`.
   Its feedback loop starts from the end-to-end reproduction required by the global bug-fixing rule.
4. **Specs.** When the user runs `/to-spec`, do not publish to an issue tracker and do not apply a triage label.
   Write the vault files below in the main session, after the skill's seam check with the user.
   Invoke `pstack:technical-writing` and `pstack:unslop` first.
   - Each item of its "User Stories" list becomes one file from `artifacts/templates/user-story.md`, named `US-nnn-<slug>.md` in `artifacts/docs/stories/`, with status `Not started` and no `sprint`.
     Take `nnn` from `artifacts/Home.md` and raise it there. Fill the story's one-sentence form, its Given/When/Then, and its estimate. Split an L before it is written.
   - The Problem Statement, Solution, and Out of Scope go into one epic from `artifacts/templates/epic.md`, and each story links to it in `epic`. Use an existing epic when the spec extends one.
   - An implementation or testing decision that meets the three ADR tests goes into `decision-log.md` as the next `D-nnn`. Any other goes into the Given/When/Then of the story it affects.
   - Write the plan once, in the stories. Do not create a spec file.
5. **Tickets.** When the user runs `/to-tickets`, do not write to `.scratch/` and do not publish to an issue tracker. A ticket is a story, so write the vault files in the main session, after the skill's quiz with the user.
   Invoke `pstack:technical-writing` and `pstack:unslop` first.
   - Each ticket becomes one story file from `artifacts/templates/user-story.md`, named `US-nnn-<slug>.md` in `artifacts/docs/stories/`, with status `Not started` and no `sprint`.
     Take `nnn` from `artifacts/Home.md` and raise it there, in dependency order with blockers first.
   - "What to build" becomes the one-sentence form, the acceptance criteria become the Given/When/Then, and "Blocked by" becomes the `Dependencies:` line with `US-nnn` codes.
   - Size each slice to an `estimate`, and split an L before it is written.
   - Link each story to its epic in `epic`.
   - When `/to-spec` already wrote stories for the same work, re-cut those files (split, merge, add `Dependencies:`) and do not create a second set.

## Plans and Scrum

There are no separate plan files. A story is the one home of its plan. Old plans are in `artifacts/archive/plans/`.
The full process is `artifacts/docs/concepts/scrum-framework.md` (decision `D-024`). Read it before sprint planning, a review, or an estimate.
The rules every session follows:

1. The user is the product owner: they order the backlog, write the sprint goal, and accept each `Done`. Claude is the development team and raises impediments as blocker pages the same day.
2. A sprint is two weeks, Monday to the Sunday of the next week. Its dates never change.
3. A story gets `sprint` only at sprint planning, for the sprint being planned, from `Ready` stories until their points reach the forecast from [[Velocity]]. Never assign a future sprint. Ask the product owner when the pick is unclear.
4. Files: `docs/stories/US-nnn-<slug>.md`, `docs/epics/EP-nn-<slug>.md`, `docs/sprints/SPR-nnn-<slug>.md`, from `templates/`. Estimates are XS=1, S=2, M=3, L=5, compared against the reference stories in the framework page. An L is split before it is `Ready`.
5. At most two stories are `In progress`. New work found mid-sprint is a backlog story and does not change the sprint goal.
6. A story reaches `Done` only when the acceptance check passes in the environment it names, tests pass, the concept page is updated with `last_updated` bumped, and the story file holds evidence (a screenshot under `artifacts/docs/stories/evidence/`) and a numbered details list. A server check needs a server screenshot. Take it before changing the status. A story not `Done` at review leaves the sprint.
7. A spike (`kind: spike`) ends with an answer in the story and a `D-nnn` decision, and works in `marie-curie/`.
8. `TODOS.md` is generated. Edit only the block between `<!-- next-action:start -->` and `<!-- next-action:end -->`. Change the source files, then run `python3 -I scripts/render_todos.py` (`--check` exits 1 when stale).
9. Every document has one code: `US-nnn`, `EP-nn`, `SPR-nnn`, `BL-nnn`, `L-nnn`, `D-nnn`. Take the next free number from `artifacts/Home.md`, raise it there, and never reuse or renumber a code.

## Write each fact once

A fact has one home and other files link to it.

- Story status, evidence, numbers, details: the story file. Epic and sprint histories record plan-level changes only.
- Decision and reason: `artifacts/docs/decisions/decision-log.md`.
- Blocker state and attempts: the blocker page.
- How a subsystem works: the concept page.
- A day's server facts: that day's log, as an index of about 20 lines with one line per event and a link. It opens with a summary of the previous day and holds no pickup list.
- Edit each vault file once per work block and make one vault commit.
- Do not put a commit hash in prose. Name a commit by story ID or message.

## Verification discipline

Details in `artifacts/docs/lessons/lessons.md`.

- Before ruling a data store out as a source, read the code that writes into it (`L-009`).
- Record a user's short answer as a decision only after checking it resolves the question asked (`L-008`).
- When an epic's Goal changes scope, re-read its other sections for the old scope (`L-005`).
- After editing a document, grep for `[[wikilinks]]` to it and recheck each referrer (`L-001`).
- Put "invoke `pstack:technical-writing` and `pstack:unslop`" in a subagent's own instructions when it drafts a document (`L-004`).
- Test region-scoped behavior with a real target-language query with diacritics (`L-007`).
- When a convention changes mid-session, recheck files created earlier in the session (`L-006`).

## artifacts/ is an Obsidian vault

`artifacts/Home.md` is the index and holds the conventions and frontmatter block (`date`, `type`, `status`, `tags`, `related`).
Load `pstack:technical-writing` and `pstack:unslop` before writing prose into any vault file.

- **`artifacts/raw/`** is the user's read-only source material. Never create, edit, rename, move, or delete anything in it. Confirm first if asked to. `raw/ideas/` holds ideas before code exists and pairs with `marie-curie/`.
- **`artifacts/logs/`** is the append-only daily scrum, one file per working day. Add a `related` link after the fact, nothing else.
- **`artifacts/archive/`** holds retired documents and is not searched. Move a finished file there with `git mv`.
- **`artifacts/docs/concepts/`** is the standing reference, one page per subsystem, cited against real file paths. Check for an existing page before writing a new one.
- **`artifacts/docs/blockers/`** holds one page per blocker, from `templates/blocker.md`. Edit `status`, `date_closed`, `approaches_tried`, and `approaches_remaining` in place, and add a dated line to its Status history on every change. A one-off issue fixed in the session goes in the day's log.

## marie-curie/ is scratch space

`marie-curie/` (repo root) holds throwaway experiments, scripts, and data dumps. Git tracks only its `README.md`.
It is the opposite of `artifacts/raw/`: create, edit, and delete freely.
Check `artifacts/raw/ideas/` for a matching idea first.
Move finished work to where it belongs (`scripts/`, `dags/`, a decision, a concept page).
Log a concluded experiment in the day's log.

## Vault edits are made in the main session

Edit every file under `artifacts/` (logs, stories, sprints, concepts, blockers, decisions, lessons) yourself.
Do not delegate vault edits to the `vault-writer` agent (`.claude/agents/vault-writer.md`).
The product owner turned it off on 2026-10-12 because it used too many tokens.
Read the story file and `git diff` before you write, and keep each edit small.
