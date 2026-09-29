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

Reviewed

## Acceptance criteria

Given a route exists and flood mode is on, when the route result panel renders, then it shows a
depth chart in 15-minute columns with the "now" column highlighted and a dashed line labeled with
the route's average depth at now, matching mockup screen 2e's "Average water depth" chart apart
from the column width. The 15-minute width replaces the 30-minute width of the first draft, see
[[fifteen-minute-cycle-tiles-and-histogram]].

## Details

1. What: `DepthForecastChart` in the route panel, drawn from `POST /flood/forecast`.
2. How: `RoutingResults.tsx` renders it when flood mode is on. `depthForecast.ts` turns the columns
   into bars, and the "now" bar is the latest column at or before now.
3. Why: it shows how depth along the route changes, so a user can decide whether to leave now or
   wait.
4. Effect: no dependency remains on [[route-forecast-query]]. The story stays `Reviewed` because
   no screenshot of the chart is saved under `evidence/`. The 2026-09-26 server check only records
   that the chart renders.

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
