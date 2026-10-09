# TODOS

The current sprint, by query. This file holds no state of its own. A story enters a sprint at sprint planning, when its `sprint` field is set. The goal, the dates, the review, and the retrospective are in the sprint file. See [[scrum-framework]].

## Current sprint: Sprint 13, 2026-10-12 to 2026-10-25

Status: planning on 2026-10-12. The goal and the picks are proposed in [[SPR-013-prove-the-storm-replay-and-finish-the-replay-stories|SPR-013]].

```dataview
TABLE title AS "Story", kind AS "Kind", priority AS "Priority", estimate AS "Estimate", status AS "Status"
FROM "docs/stories"
WHERE type = "user-story" AND sprint = 13
SORT priority ASC, file.name ASC
```

## Product backlog, top of the order

```dataview
TABLE title AS "Story", kind AS "Kind", priority AS "Priority", estimate AS "Estimate", status AS "Status"
FROM "docs/stories"
WHERE type = "user-story" AND !sprint AND status != "Done" AND status != "Superseded"
SORT priority ASC, file.name ASC
LIMIT 10
```

## Open blockers

See the [[Blockers board]]. Each blocker page says whether it blocks the sprint goal.
