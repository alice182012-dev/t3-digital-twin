---
date_drafted: 2026-09-23
type: user-story
status: draft
subsystem: floodmap-frontend
sprint: 3
source_ideas: []
related: ["[[flood-routing-mockup-frontend-gap]]", "[[route-forecast-query]]", "[[sprint-plan]]", "[[verify-table-capability-against-write-path-not-summary-or-current-query]]"]
tags: [user-story, sprint-3]
---

# Depth-versus-time forecast chart

## User story

As a user planning a route through a flood-prone area, I want to see how depth along my route is
expected to change over the next couple of hours, so I can decide whether to leave now or wait.

## Priority

P0

## Estimate

M

## Status

Done

## Acceptance criteria

Given a route exists and flood mode is on, when the route result panel renders, then it shows a
depth chart in 15-minute columns with the "now" column highlighted and a dashed line labeled with
the route's average depth at now, matching mockup screen 2e's "Average water depth" chart apart
from the column width. The 15-minute width replaces the 30-minute width of the first draft, see
[[fifteen-minute-cycle-tiles-and-histogram]].

## Evidence

![[depth-forecast-chart-server-check.png|420]]

Caption: the live frontend at `100.67.84.55:8082`, captured 2026-09-30 from a Mac browser at 1366x768, for a car route of 4.5 km from 21.0000, 105.7450 to 21.0060, 105.7520. The flood pipeline was paused, so the newest data ends at 2026-09-30 03:45. The browser clock was set to 2026-09-29 17:00 +07:00 so the "Now" column falls inside the retained runs. The backend and the data are the real ones.

## Details

1. What: `DepthForecastChart` in the route panel, drawn from `POST /flood/forecast`. The screenshot shows seven columns from 16:45 to 18:15, "Now" highlighted at 17:00, and the dashed line labeled 1 cm.
2. How: `RoutingResults.tsx` renders it when flood mode is on. `depthForecast.ts` turns the columns into bars, and the "now" bar is the latest column at or before now.
3. Why: it shows how depth along the route changes, so a user can decide whether to leave now or wait.
4. Effect: no dependency remains on [[route-forecast-query]]. A hand calculation resampled the route (183 samples over 4,530 m) and read every sample's pixel with a separate `ST_Value` query. The 17:00 column gave a mean of 0.0069 m, a maximum of 0.185 m, and a wet fraction of 0.071, and the 18:15 column gave 0.0151 m, 0.344 m, and 0.087. The endpoint returned the same figures. A second route (56 samples) matched the same way.

## Status history

- **2026-09-23, draft.** Not assigned to a sprint. `GET /flood/points`
  ([[point-depth-lookup-backend]]) gives one point's depth at one timestep. This story needs depth
  averaged along a whole route across five 30-minute columns, which no endpoint scopes today. See
  [[flood-routing-mockup-frontend-gap]]'s Risks and open questions for the three options on the
  table: build a narrower forecast endpoint, reopen `GET /flood/forecast` or
  `GET /flood/route/forecast` in [[t3-digital-twin-architecture-gaps]], or drop this goal. Revisit
  once that decision is made, then move into [[sprint-plan]].
- **2026-09-23, draft.** Assigned to Sprint 3, alongside [[frontend-depth-features]]'s other
  `GET /flood/points`-dependent stories. Data source resolved: `flood_road_values` already holds a
  full per-segment forecast time series (see [[route-forecast-query]], Sprint 2), reversing the
  earlier "no data source" conclusion. See
  [[verify-table-capability-against-write-path-not-summary-or-current-query]]. Dependency:
  [[route-forecast-query]] must land first, and its own open question (how to match a route's
  segments against `flood_road_values`'s rows) must resolve before this story starts.
- **2026-09-26, draft.** Built on `fifteen-minute-cycle` and deployed to the server. The chart
  reads `POST /flood/forecast`, which samples the depth raster tiles along the route, not
  `flood_road_values`, so the segment-matching question no longer applies. Columns are 15 minutes
  wide.
- **2026-09-29, draft.** Status moved from `Not started` to `Reviewed`. Acceptance criteria and
  details rewritten to match the code. Needs a screenshot of the chart on the server to reach
  `Done`. A check of the average-depth value against a hand calculation from the raster is also
  still missing, and the earlier risk of a plausible but wrong average makes that check worth
  doing.
- **2026-09-30, draft.** Status moved from `Reviewed` to `Done`. Saved `depth-forecast-chart-server-check.png` and hand-checked two columns against `flood_depth_raster_tile`, see Details. The screenshot needed a browser clock override, because `flood_mapping_full` is paused and its newest data is older than the eight-column window.
