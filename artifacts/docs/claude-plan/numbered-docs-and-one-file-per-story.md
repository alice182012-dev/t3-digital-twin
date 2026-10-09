---
date: 2026-10-09
type: plan
status: active
tags: [plan, vault, numbering, user-stories, sprint-plan]
related: ["[[Home]]"]
---

# Number the vault documents and give every story its own file

The user asked on 2026-10-09 for numeric codes on stories, PRDs, and blockers, one file per story, and sprints outside the stories folder. The user chose these options: prefix plus number, split by folder, and a scripted migration on a local branch.

## Target layout

| Kind | Folder | File name | Code |
| ---- | ------ | --------- | ---- |
| Story | `docs/stories/` | `US-094-archive-results-3di.md` | `US-nnn`, unchanged |
| Epic | `docs/epics/` | `EP-01-<slug>.md` | `EP-nn`, ordered by first story ID |
| Sprint plan | `docs/sprints/` | `SP-03-<slug>.md` | `SP-nn`, equal to `plan_number` |
| PRD | `docs/prds/` | `PRD-001-<slug>.md` | `PRD-nnn`, ordered by `date_drafted` |
| Blocker | `docs/blockers/` | `BL-001-<slug>.md` | `BL-nnn`, ordered by `date_open` |
| Lesson | `docs/lessons/` | `L-001-<slug>.md` | `L-nnn`, ordered by `date_captured` |

Concept pages, logs, and plans keep their names.

## Rules after the move

1. A story file owns its status, priority, estimate, sprint, epic, evidence, and details. Nothing else holds a second copy.
2. A sprint file holds the goal, the dates, the risks, and the history. Its story list is a Dataview query over the story frontmatter, so moving a story to another sprint is one edit in the story.
3. An epic file holds the shared intro and a link list of its stories.

## Steps

1. Phase A, mechanical: rename, split epics into story files, rewrite every wikilink. Script in `marie-curie/numbering_migration/`, with a dry run and a link check. One commit on branch `artifacts-numbering`, not pushed.
2. Phase B, sprint tables: move each row's priority, estimate, status, dependencies, evidence, and details into its story, then replace the hand tables with Dataview queries. A second commit.
3. Update `Home.md` conventions, `.claude/CLAUDE.md`, the templates, and `TODOS.md` links, and set the next free `PRD`, `BL`, `L`, and `EP` numbers.

## Status

- 2026-10-09: plan written, branch `artifacts-numbering` created.
