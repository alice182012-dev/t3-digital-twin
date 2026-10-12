---
date: 2026-10-12
type: sprint
sprint_id: "SPR-014"
sprint: 14
start_date: 2026-10-12
end_date: 2026-10-25
status: active
tags: [sprint]
related: ["[[scrum-framework]]", "[[Velocity]]", "[[SPR-013-prove-the-storm-replay-and-finish-the-replay-stories|SPR-013]]", "[[decision-log|D-038]]", "[[decision-log|D-040]]"]
---

# SPR-014 Sprint 14: Finish the edge depth table replacement

## Sprint goal

Finish [[decision-log|D-038]]: every reader of flood depth reads the edge depth table, and the old sampler and `flood_road_values` are deleted.

Confirmed by the product owner on 2026-10-12. The goal does not change after the sprint starts.

## Planning

- **Dates.** The sprint runs two weeks, from Monday 2026-10-12 to Sunday 2026-10-25. It started on the day [[SPR-013-prove-the-storm-replay-and-finish-the-replay-stories|SPR-013]] ended early, at the product owner's request ([[decision-log|D-040]]).
- **Velocity.** The last sprints gave 15, 25, and 10 points ([[Velocity]]), and the last one lasted one day. The forecast stays at 16 points, as the product owner set it for Sprint 13.
- **Picks.** Seven stories make 17 points. Each one is `Ready` (the INVEST check of [[scrum-framework]]), and the sum passes the forecast with the last pick, as the rule asks. The table lists them in the order to start them.

| Order | Story | Title | Estimate | Points | Depends on |
| ----- | ----- | ----- | -------- | ------ | ---------- |
| 1 | [[US-118-write-the-edge-depth-to-a-queryable-table\|US-118]] | Write the edge depth to a queryable table | M | 3 | none, in progress since 2026-10-12 |
| 2 | [[US-106-keep-per-segment-depth-history-in-timescaledb\|US-106]] | Write per-segment depth history to TimescaleDB (part a) | M | 3 | none, `Reviewed` |
| 3 | [[US-113-backfill-per-segment-depth-history\|US-113]] | Backfill per-segment depth history | S | 2 | US-106 |
| 4 | [[US-120-read-the-rain-gate-and-soak-checks-from-the-edge-table\|US-120]] | Read the rain gate and the soak checks from the edge table | S | 2 | US-118 |
| 5 | [[US-121-read-the-flood-metrics-from-the-edge-table\|US-121]] | Read the flood metrics from the edge table | M | 3 | US-118 |
| 6 | [[US-122-point-depth-history-at-the-edge-table\|US-122]] | Point depth_history at the edge table | S | 2 | US-118, US-106, US-113 |
| 7 | [[US-123-delete-flood-on-roads-and-flood-road-values\|US-123]] | Delete flood_on_roads, road_segment, and flood_road_values | S | 2 | US-119 (`Done`), US-120, US-121, US-122 |
| | | Total | | 17 | |

- **Why these.** [[US-123-delete-flood-on-roads-and-flood-road-values|US-123]] needs every reader moved, and [[US-122-point-depth-history-at-the-edge-table|US-122]] needs [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]] and [[US-113-backfill-per-segment-depth-history|US-113]] `Done`. So the goal needs all seven.
- **Risk.** [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]] needed one event-triggered `flood_history` run. It passed on 2026-10-12 with a hand-made asset event, so the rain no longer blocks the chain. The story still waits for the compression measurement and the owner's acceptance, and [[US-113-backfill-per-segment-depth-history|US-113]] can then load the retained runs.
- **Work in progress.** At most two stories are `In progress` at once. Only [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]] is, on 2026-10-12.
- **Done outside the plan.** [[US-117-export-a-stable-key-with-each-graph-edge|US-117]] and [[US-119-read-the-map-overlay-and-route-fallback-from-the-edge-table|US-119]] were done on 2026-10-12 before this sprint was planned. They have no `sprint`, and their points are not in [[Velocity]].
- **Open decisions.** None.

## Sprint backlog

```dataview
TABLE title AS "Story", kind AS "Kind", priority AS "Priority", estimate AS "Estimate", status AS "Status", epic AS "Epic"
FROM "docs/stories"
WHERE sprint = 14
SORT priority ASC, file.name ASC
```

## Review

Fill this on 2026-10-25. Walk through each story that is `Done` by its evidence screenshot, and record the product owner's accept or reject.

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

- **2026-10-12, planning.** Created at the product owner's request, with the goal "Finish D-038". The product owner confirmed the goal the same day.
- **2026-10-12, active.** The product owner ended [[SPR-013-prove-the-storm-replay-and-finish-the-replay-stories|SPR-013]] early and started this sprint the same day, from 2026-10-12 to 2026-10-25 ([[decision-log|D-040]]). Seven stories are picked, with `sprint: 14`, and they make 17 points.
