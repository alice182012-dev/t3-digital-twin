---
date_drafted: 2026-09-23
type: user-story
status: draft
subsystem: architecture-backend
sprint: 2
source_ideas: []
related: ["[[t3-digital-twin-architecture-gaps]]", "[[depth-forecast-chart]]", "[[sprint-plan]]", "[[verify-table-capability-against-write-path-not-summary-or-current-query]]"]
tags: [user-story, backend, sprint-2]
---

# Route-forecast query against `flood_road_values`

## User story

As a frontend developer building the depth-versus-time forecast chart, I want a query that returns
a route's average depth in 30-minute buckets across the forecast window, so the chart has a real
data source instead of an unbuilt endpoint.

## Priority

P1

## Estimate

M

## Acceptance criteria

Given a completed `constant_cycle` run and a route whose segments intersect flooded road geometry,
when the route-forecast query runs for that route, then it returns one average depth value per
30-minute bucket spanning the run's forecast window, matching values computable by hand from
`flood_road_values`'s raw per-segment `timeseries` rows for one spot-checked bucket.

## Status history

- **2026-09-23, draft.** `flood_road_values` already holds a full per-segment forecast time series
  per run (`scripts/database/geojson_to_pg.py`'s `build_rows` writes one row per `(segment,
  forecast timestep)` pair), reversing an earlier "no data source" conclusion for
  [[depth-forecast-chart]]. See [[t3-digital-twin-architecture-gaps]]'s Goals and Dependencies and
  assumptions, and [[verify-table-capability-against-write-path-not-summary-or-current-query]].
  Open dependency: the table has no stable segment ID, only `road_name` (which repeats) and
  `geom_4326`, so matching a route's segments against it needs either a GraphHopper path-detail or
  a spatial join, not yet decided.

This is the simple story shape: one sprint, one objective. See [[user-story-types]] for the epic,
thematic, and SAFe shapes and when each one fits. Move `status` to `ready` once acceptance criteria
are settled, `in-progress` once work starts, or `done` once the acceptance criteria pass.
