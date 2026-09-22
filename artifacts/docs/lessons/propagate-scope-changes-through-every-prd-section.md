---
date_captured: 2026-09-23
type: lesson
status: active
subsystem: architecture-backend
source_blockers: []
tags: [lesson, prd]
related: ["[[t3-digital-twin-architecture-gaps]]"]
---

# When a PRD's Goals change, propagate the change through every other section

## Rule

After editing a PRD's Goals to add or remove scope, re-read Problem, Non-goals, Dependencies and
assumptions, Definition of done, and Rollback for sentences that assumed the old scope. A Goals
edit alone leaves the rest of the document telling a story that no longer matches it.

## Why

The user marked four of `t3-digital-twin-architecture-gaps.md`'s six Goals "no need" (the
fast-track trigger, Redis, citizen endpoints, council dashboard), directly in the Goals list. Every
other section had been written assuming those four existed: Problem's "this matters because" case
cited the citizen and dashboard endpoints and the fast-track trigger by name; Non-goals had no
bullet for them since they weren't yet excluded, they were assumed built; Dependencies had a
fast-track DAG-ordering bullet and a Redis-naming bullet that no longer applied; Definition of done
had four bullets checking behavior that would never be built; Rollback listed services that would
never be stood up. Fixing only Goals would have shipped a PRD that contradicted itself in five
places.

## How to apply

Treat a Goals-list edit that adds or removes an item as a trigger to re-read the whole PRD, not
just confirm the edit landed. Grep the PRD for the removed or added goal's key terms (an endpoint
name, a service name) across every other section, and update or delete each hit. This is slower
than editing Goals alone, but a PRD with a stale Definition of done is worse than one that took
longer to update, since it will still read as authoritative for years and no error message reports
a stale sentence.

## Source blockers

- None. Surfaced from the same-session descoping edit to `t3-digital-twin-architecture-gaps.md`.

## Status history

- **2026-09-23, active.** Captured after descoping four of six Goals and finding stale references
  in Problem, Non-goals, Dependencies and assumptions, Definition of done, and Rollback.
