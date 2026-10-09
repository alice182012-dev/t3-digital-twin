## gstack (REQUIRED, global install)

The hook `.claude/hooks/check-gstack.sh` blocks skill use when gstack is missing and prints the install steps.
If it blocks, stop and tell the user to install it
(`git clone --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack`, then
`cd ~/.claude/skills/gstack && ./setup --team`, then restart).
Do not skip skills or work around a missing gstack.
Use `/browse` for all web browsing.

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

When a request matches a skill, invoke it. When in doubt, invoke it.
Ideas: `/office-hours`. Scope: `/plan-ceo-review`. Architecture: `/plan-eng-review`. Design: `/design-consultation`, `/plan-design-review`.
Bugs: `/investigate`. QA: `/qa`, `/qa-only`. Review: `/review`. Visual polish: `/design-review`.
Ship: `/ship`, `/land-and-deploy`. Save or resume: `/context-save`, `/context-restore`. Spec: `/spec`.

gstack owns the lifecycle and pstack owns how code is written.
Implementation goes through `pstack:poteto-mode`.
Review a diff first with `pstack:interrogate`, then `/review` as the pre-ship gate.
Use gstack for business altitude ("safe to ship") and pstack for engineering altitude ("well structured").

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

## Vault edits go to the vault-writer agent

Delegate every edit under `artifacts/` (logs, stories, sprints, concepts, blockers, decisions, lessons) to the `vault-writer` agent (`.claude/agents/vault-writer.md`, Haiku).
Keep the brief short: the story ID, the task, and the date. The agent reads `git log`, `git diff`, and the story file for the rest.
Add a sentence only for a fact that exists nowhere in the repo, such as a measured number, a server result, or a user decision.
Read what it wrote before you report it as done.
Edit code, DAGs, and scripts yourself. The agent does not touch them.
