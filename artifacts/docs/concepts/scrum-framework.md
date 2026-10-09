---
date: 2026-10-10
type: concept
status: active
last_updated: 2026-10-10
tags: [concept, scrum, process]
related: ["[[decision-log|D-024]]", "[[Velocity]]", "[[Home]]", "[[SPR-013-prove-the-storm-replay-and-finish-the-replay-stories|SPR-013]]"]
---

# Scrum framework

How this project plans and tracks work. It follows the Scrum framework as Atlassian describes it. The readings are in `docs/concepts/project-management/`. The decision to adopt it is [[decision-log|D-024]]. `.claude/CLAUDE.md` holds the rules in short form and links here.

## Roles

- **Product owner:** the user. They order the backlog, write the sprint goal, and accept or reject each `Done`. There is one product owner.
- **Development team:** Claude sessions. They estimate, build, and gather evidence.
- **Scrum master duties:** keep the events on time and raise impediments. A blocker page is an impediment. Claude raises it the same day it is found.

## Cadence

A sprint is one week, Monday to Sunday. The next sprint starts the next Monday. A sprint's dates never change after it starts, and the sprint number never skips. The sprint file is `docs/sprints/SPR-nnn-<slug>.md`, where nnn is the sprint number.

| Day | Event | Time limit |
| --- | ----- | ---------- |
| Monday | Sprint planning | 2 hours |
| Tuesday to Saturday | Daily log | each day |
| Sunday | Sprint review, retrospective, then refinement | about 1 hour 15 minutes |

## Hierarchy

Theme, then epic, then story.

- **Theme:** a long-running goal (`flood-data`, `routing`, `frontend`, `paper`). It is a frontmatter field of an epic and has no file.
- **Epic** (`docs/epics/EP-nn-<slug>.md`): a body of work of several weeks with a goal, a reason, assumptions, a definition of done, and a list of its stories by query. The epic replaces the retired PRD. Keep the number small.
- **Story** (`docs/stories/US-nnn-<slug>.md`): work that fits one sprint. `kind` is `story` (user value), `spike` (a question with a timebox), or `bug`.

A story that is not part of an epic is allowed, but rare.

## Artifacts

- **Product backlog:** every story with `sprint` empty and a status other than `Done` or `Superseded`, ordered by `priority`. It has no file. Obsidian reads it with a query.
- **Sprint backlog:** every story with `sprint: N`. Setting `sprint` is the pick, and only sprint planning does it.
- **Increment:** the stories that are `Done` at the review, shown by their evidence.

## Story lifecycle

`Not started` (in the backlog), then `Ready`, then `In progress`, then `Reviewed`, then `Done`. `Blocked` and `Superseded` can happen at any point.

- **Ready:** the acceptance check, the estimate, and the dependencies are written, and a story rated L is split.
- **Reviewed:** built and read through. The acceptance check has not passed.
- **Done:** the Definition of done below holds.
- A story that is not `Done` at the review leaves the sprint. Its `sprint` is cleared and it is estimated again.

## Definition of done

One definition, for every story:

1. The acceptance check passes in the environment it names (the server, when it says server).
2. Tests pass.
3. The concept page that the story changes is updated, and `last_updated` is bumped.
4. **Evidence** is in the story file under "Evidence and details". A UI story gets a screenshot of the running UI. A backend story with no UI gets a screenshot of the real output, with a caption that gives the capture time and host. A **spike** records its measured result and a decision in `decision-log.md`, and needs no screenshot.
5. **Details** is a numbered list in the story file: what was built, how, why, and what it changes for later stories.
6. The product owner accepts it at the review.

Take the screenshot before changing the status. If the check fails, open a blocker and leave the story off `Done`.

## Estimates and velocity

Estimates are XS (1), S (2), M (3), and L (5). A story rated L is split before it enters a sprint. [[Velocity]] shows the points that were `Done` in each sprint. Sprint planning uses the last three values.

## The events

**Refinement** (end of the previous sprint, about 30 minutes). Order the top of the backlog, split any story rated L, write the Given, when, then of each story near the top, and write unknowns as questions, not as vague words. A refined story becomes `Ready`.

**Sprint planning** (Monday, 2 hours at most).

1. Read [[Velocity]] and decide the forecast in points.
2. The product owner writes the sprint goal in one sentence.
3. Pick `Ready` stories from the top of the backlog until the points reach the forecast. Stories that threaten the goal come first.
4. Set `sprint: N` on the picked stories.
5. Create the sprint file from `templates/sprint.md`. Schedule the start of any long run (a 12-hour replay) now.

**Daily log.** The daily log under `artifacts/logs/` is the daily scrum. Start it with what moved, what moves today, and what blocks. Write one line per event and link to the story, blocker, or decision that holds the detail. The log starts with a summary of the previous day.

**Execution.** Take the top story that is not started, set it `In progress`, and keep only a few in progress at once. New work found during the sprint goes to the backlog. It enters the sprint only if it threatens the goal, and then the product owner decides what leaves. A blocker found in the sprint gets a blocker page the same day.

**Sprint review** (last day, 30 minutes). Walk through each `Done` story by its evidence. The product owner accepts or rejects it. Record the result in the sprint file's Review section.

**Retrospective** (last day, 15 minutes). Write what worked, what did not, and one action. Check the last action first. An action becomes a story, a rule change, or an `L-nnn` lesson.

## Blockers

A blocker is an impediment. It gets a page from `templates/blocker.md`. If it blocks the sprint goal, it is first in the daily log until it is `resolved`. If it does not, it waits for planning. The blocker page says which case it is, and why.

## Ideas and spikes

An idea is a note in `raw/ideas/` (the user's, read-only for Claude). An experiment on it is a spike story with `source_ideas` pointing at the note. The work happens in `marie-curie/`. The spike ends with an answer in the story and a `D-nnn` decision. A go becomes real stories, which go through refinement like any other. At each review Claude lists the ideas whose spike might come next, and the product owner picks.

## Where each fact lives

| Fact | Home |
| ---- | ---- |
| Status, sprint, estimate, evidence, details of a story | the story file |
| The goal, dates, review, and retrospective of a sprint | the sprint file |
| The goal, reason, and definition of done of an epic | the epic file |
| A decision, including a spike's outcome | `decision-log.md` |
| An impediment and its attempts | the blocker page |
| A day's events | the daily log |
| The current sprint's stories | `TODOS.md`, by query, no state of its own |
| Points done by sprint | [[Velocity]], by query |

## What changed on 2026-10-10

- The four-sprint plan (`SP-nn`) and its pre-assigned future sprints are retired. A sprint is picked at planning, one at a time. The old plans are in `archive/sprints/`.
- PRDs are retired. The four PRDs are in `archive/prds/`, and each epic holds what its PRD held.
- The 16 epics became 4 (`EP-17` to `EP-20`). The old ones are in `archive/epics/`.
- `TODOS.md` no longer holds state. It shows the current sprint.
- Sprints 1 to 12 were not weeks. Their `sprint` values stay on `Done` stories for history. Sprint 13 starts on 2026-10-12, a Monday.
