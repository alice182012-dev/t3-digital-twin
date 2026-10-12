---
date: 2026-10-12
type: sprint
sprint_id: "SPR-014"
sprint: 14
start_date: 2026-10-26
end_date: 2026-11-08
status: planning
tags: [sprint]
related: ["[[scrum-framework]]", "[[Velocity]]", "[[SPR-013-prove-the-storm-replay-and-finish-the-replay-stories|SPR-013]]", "[[decision-log|D-038]]"]
---

# SPR-014 Sprint 14: Finish the edge depth table replacement

## Sprint goal

Finish [[decision-log|D-038]]: every reader of flood depth reads the edge depth table, and the old sampler and `flood_road_values` are deleted.

This is a draft goal from the product owner, set on 2026-10-12. The product owner confirms or changes it at planning on 2026-10-26. The goal does not change after the sprint starts.

## Planning

- **Dates.** The sprint runs two weeks, from Monday 2026-10-26 to Sunday 2026-11-08, the Monday after [[SPR-013-prove-the-storm-replay-and-finish-the-replay-stories|SPR-013]] ends ([[decision-log|D-026]]). Planning is on 2026-10-26.
- **Velocity.** Read [[Velocity]] after the review of Sprint 13 on 2026-10-25, and set the forecast then.
- **Picked stories.** None yet. A story gets `sprint: 14` only at planning, so no story has it today.
- **Candidates.** The open stories of [[decision-log|D-038]], in the order of their dependencies. They total 11 points, plus the rest of [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]] if it is not `Done` by then.

| Order | Story | Title | Estimate | Status on 2026-10-12 |
| ----- | ----- | ----- | -------- | -------------------- |
| 1 | [[US-120-read-the-rain-gate-and-soak-checks-from-the-edge-table\|US-120]] | Read the rain gate and the soak checks from the edge table | S | Not started |
| 2 | [[US-121-read-the-flood-metrics-from-the-edge-table\|US-121]] | Read the flood metrics from the edge table | M | Not started |
| 3 | [[US-122-point-depth-history-at-the-edge-table\|US-122]] | Point depth_history at the edge table | S | Not started |
| 4 | [[US-123-delete-flood-on-roads-and-flood-road-values\|US-123]] | Delete flood_on_roads, road_segment, and flood_road_values | S | Not started |

- **Open decisions.** None. The goal is a draft until planning.

## Sprint backlog

```dataview
TABLE title AS "Story", kind AS "Kind", priority AS "Priority", estimate AS "Estimate", status AS "Status", epic AS "Epic"
FROM "docs/stories"
WHERE sprint = 14
SORT priority ASC, file.name ASC
```

## Review

Fill this on 2026-11-08. Walk through each story that is `Done` by its evidence screenshot, and record the product owner's accept or reject.

- **Goal met:** yes or no, with one sentence.
- **Points delivered:** N of N forecast.
- **Not done:** each story that left the sprint, back to the backlog with `sprint` cleared.
- **Estimate misses:** each `Done` story whose size was clearly wrong, with the number it should have had (1, 2, 3, or 5). Check that the reference stories in [[scrum-framework]] still fit.

## Retrospective

Three bullets and one action. Check the last retrospective's action first.

- **Worked:**
- **Did not work:**
- **Action:** a story, a rule change, or an `L-nnn` lesson.

## Refinement for the next sprint

The top of the backlog after this review: the order, the stories split, and the questions to answer.

## Status history

- **2026-10-12, planning.** Created at the product owner's request, with the draft goal "Finish D-038". The sprint has no picked story, and the dates are fixed.
