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

## Acceptance criteria

Given a route exists, when the route result panel renders, then it shows a 30-minute-column depth
chart with the "now" column highlighted and a dashed line labeled with the route's current average
depth, matching mockup screen 2e's "Average water depth" chart.

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
