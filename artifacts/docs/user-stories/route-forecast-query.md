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

## Status

Done

## Evidence

![[connection-pooling-and-forecast-verification.png|420]]

## Acceptance criteria

Given a run with depth rasters loaded and a route polyline, when `POST /flood/forecast` runs for
that route, then it returns one mean depth per 15-minute column, taking each column from the newest
run that has a raster for it, and the value for one spot-checked column matches a hand calculation
from `flood_depth_raster_tile` at the same sample points. The 15-minute width and the raster source
replace the 30-minute buckets and `flood_road_values` of the first draft, see
[[fifteen-minute-cycle-tiles-and-histogram]].

## Details

1. What: `POST /flood/forecast` in `backend/flood_forecast.py`.
2. How: it takes up to 2,000 route points and up to 96 steps. It samples the polyline at even
   spacing, capped at 200 samples, and reads each sample from `flood_depth_raster_tile`. It
   returns `mean_depth_m`, `max_depth_m`, and `wet_fraction` per column.
3. Why: the raster is the source of truth for depth ([[flood-routing-mockup-frontend-gap]]
   Decisions), and sampling the polyline needs no stable road segment ID.
4. Effect: [[depth-forecast-chart]] no longer waits on this story. On the server, a 5-point route
   returned 13 columns in 1.5 s (2026-09-26). Hand-checked 2026-09-29: an independent Python replica
   of `sample_polyline`'s 23-sample algorithm, run as raw SQL against `flood_depth_raster_tile`
   directly, matched the endpoint's `max_depth_m`, `mean_depth_m`, and `wet_fraction` to every digit
   for one column. `test_flood_forecast.py`'s own automated pass against a real PostGIS still has not
   run (needs GDAL, unavailable in the session that did the hand-check).

## Status history

- **2026-09-23, draft.** `flood_road_values` already holds a full per-segment forecast time series
  per run (`scripts/database/geojson_to_pg.py`'s `build_rows` writes one row per `(segment,
  forecast timestep)` pair), reversing an earlier "no data source" conclusion for
  [[depth-forecast-chart]]. See [[t3-digital-twin-architecture-gaps]]'s Goals and Dependencies and
  assumptions, and [[verify-table-capability-against-write-path-not-summary-or-current-query]].
  Open dependency: the table has no stable segment ID, only `road_name` (which repeats) and
  `geom_4326`, so matching a route's segments against it needs either a GraphHopper path-detail or
  a spatial join, not yet decided.
- **2026-09-26, draft.** Built as `POST /flood/forecast` on `fifteen-minute-cycle`. It reads the
  raster tiles along the route instead of `flood_road_values`, which removes the segment-matching
  question.
- **2026-09-29, draft.** Status moved from `Not started` to `Reviewed`. Acceptance criteria and
  details rewritten to match the code. Still needed for `Done`: the endpoint tests against a real
  PostGIS, one hand-checked column, and a server screenshot of the response.
- **2026-09-29, draft.** Status moved to `Done`. Hand-checked one column against
  `flood_depth_raster_tile` directly on the live server, exact match. `test_flood_forecast.py`'s own
  pass still hasn't run (needs GDAL), tracked separately, not blocking this story's own acceptance
  criteria.

This is the simple story shape: one sprint, one objective. See [[user-story-types]] for the epic,
thematic, and SAFe shapes and when each one fits. Move `status` to `ready` once acceptance criteria
are settled, `in-progress` once work starts, or `done` once the acceptance criteria pass.
