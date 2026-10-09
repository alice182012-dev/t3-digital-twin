---
date_captured: 2026-09-23
type: lesson
status: active
subsystem: floodmap-frontend
source_blockers: []
tags: [lesson, session-hygiene, user-story]
related: ["[[US-001-depth-forecast-chart|depth-forecast-chart]]", "[[US-017-route-forecast-query|route-forecast-query]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
---

# When a shared convention file changes mid-session, recheck files already created against it

## Rule

After noticing a project convention file (`.claude/CLAUDE.md`, `Home.md`) changed on disk mid-
session, check files already created earlier in the same session against the new rule, not only
files created after noticing the change.

## How to apply

A "file changed on disk" notice is a prompt to ask "does anything I already wrote need to change
too," not only "does my next edit need to account for this." Grep for the artifact kind the
convention covers (here, `type: user-story` with a Simple shape) and check each one's frontmatter
or structure against the updated rule before moving on.

## Why

`.claude/CLAUDE.md`'s "User stories and sprint planning" section was refined mid-session (likely by
the user, outside this session's own edits) to add: a Simple-shape story carries its schedule as a
`sprint` frontmatter field, not row fields, since it has only one row to schedule. Two Simple-shape
stories, `depth-forecast-chart.md` and `route-forecast-query.md`, had already been created earlier
in the same session without that field, using tags and prose instead. The change was noted as "take
it as current state" per the session's own convention, but the two already-written files weren't
checked against it until this lesson's own drafting prompted a search.

## Source blockers

- None. Surfaced from noticing two already-created files didn't match a convention that had
  changed since they were written.

## Status history

- **2026-09-23, active.** Captured while auditing this session's user-story files against
  `.claude/CLAUDE.md`'s current "User stories and sprint planning" section.
