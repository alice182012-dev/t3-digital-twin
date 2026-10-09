---
date: 2026-10-10
type: sprint
sprint_id: "SPR-013"
sprint: 13
start_date: 2026-10-12
end_date: 2026-10-25
status: planning
tags: [sprint]
related: ["[[scrum-framework]]", "[[Velocity]]", "[[decision-log|D-024]]"]
---

# SPR-013 Sprint 13: prove the storm replay and finish the replay stories

The first sprint under Scrum ([[decision-log|D-024]]). It runs two weeks, from Monday 2026-10-12 to Sunday 2026-10-25 ([[decision-log|D-026]]). Planning is on 2026-10-12. This file holds a proposal until the product owner confirms the goal and the picks.

## Sprint goal

Proposed: the pipeline passes a full-storm replay with the `US-101` fix, and the stories that read that replay (`US-089` and `US-091`) are `Done`.

## Planning

- **Velocity.** The last three sprints gave 7, 15, and 25 points ([[Velocity]]). Those sprints lasted days, not two weeks, so they under-measure a two-week sprint. A planning range is 16 points (the average) to 25 points (the best of the three). The product owner sets the forecast on Monday, and Sprint 13 calibrates the next one.
- **Proposed picks.** `US-102` (S, P0), `US-089` (M, P1), and `US-091` (M, P1) make 8 points. They share one 12-hour replay, so the replay is the critical path and starts on Monday.
- **Room for 8 to 17 more points.** The ready stories with no dependency on the replay are `US-076` (M), `US-085` (S), `US-079` (XS), and `US-080` (XS), which are frontend recheck rows (7 points). Other `Ready` stories can fill the rest after refinement. The product owner said on 2026-10-08 that routing finishes first, so these are the product owner's choice.
- **Work in progress.** At most two stories are `In progress` at once. `US-102` starts first on Monday, because the replay is the longest wait.
- **Not picked.** `US-094` waits for real rain above 5 mm/h and cannot finish this sprint.

**Open decisions for the product owner at planning:**

1. Confirm the goal and the picks above. Setting `sprint: 13` on a story is the pick.
2. Give the go for the 12-hour replay (`US-102`).
3. Decide whether `TIME_AWARE_ROUTING` goes on for good (`rollout.ps1 -LeaveOn` and `TIME_AWARE_ROUTING=true` in `.env`), best with the DAG running on real rain.
4. Decide what to do about the growth of `9c` within a chain ([[BL-023-9c-sampling-step-runs-over-770-seconds|BL-023]], 46 s to 96 s, cause unknown), or leave the blocker at `monitoring`.

## Sprint backlog

```dataview
TABLE title AS "Story", kind AS "Kind", priority AS "Priority", estimate AS "Estimate", status AS "Status", epic AS "Epic"
FROM "docs/stories"
WHERE sprint = 13
SORT priority ASC, file.name ASC
```

## Review

Fill this on 2026-10-25.

## Retrospective

Fill this on 2026-10-25.

## Refinement for the next sprint

Fill this on 2026-10-25.

## Status history

- **2026-10-10, planning.** Created at the Scrum adoption ([[decision-log|D-024]]) so the first sprint has a home. Every story that was not `Done` returned to the backlog with `sprint` cleared. The old Sprint 13 to 16 placement of the frontend recheck ([[SP-04-frontend-recheck|sprint-plan-4]]) is dropped.
- **2026-10-10, planning.** The sprint length changed from one week to two weeks, and stories enter by story points and not by weeks ([[decision-log|D-026]]). The end date moved from 2026-10-18 to 2026-10-25. The picks stay unset until planning on 2026-10-12.
