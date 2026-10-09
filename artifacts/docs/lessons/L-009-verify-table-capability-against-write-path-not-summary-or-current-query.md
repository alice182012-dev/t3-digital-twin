---
date_captured: 2026-09-23
type: lesson
status: active
subsystem: architecture-backend
source_blockers: []
tags: [lesson, verification, postgis, flood_road_values]
related: ["[[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]]", "[[PRD-001-flood-routing-mockup-frontend-gap|flood-routing-mockup-frontend-gap]]", "[[US-001-depth-forecast-chart|depth-forecast-chart]]"]
---

# Verify a table's capability against its write path, not a summary or its current query

## Rule

Before concluding a data store can't serve a need, read the code that writes rows into it, not
just a one-line schema summary or the query code that happens to read it today. A table can hold
more than its current consumers ask of it.

## Why

Ruled `flood_road_values` out as a source for the depth-versus-time forecast chart, reasoning from
two things: the architecture doc's one-line description ("PostGIS `flood_road_values` (keyed
`timestamp, forecast_time`)") and `flood_areas.py`'s `derive_areas`, which queries it with
`WHERE forecast_time = %(valid_time)s`, a single timestep. Both read as "this table holds one
snapshot per query," and neither was wrong on its own. What was missing was
`scripts/database/geojson_to_pg.py`'s `build_rows`, the function that actually inserts rows: for
every road segment, it iterates that segment's full `timeseries` array from the source GeoJSON and
writes one row per `(segment, forecast timestep)` pair. Since `constant_cycle` runs 25 timesteps at
15-minute resolution over 6 hours, the table already holds a complete per-segment depth time
series per run, not a single value. `flood_areas.py` only ever filters to one `forecast_time`
because its two consumers (route grading, map overlay) only ever need "right now," not because the
table can't hold more. Reading the current query's `WHERE` clause and mistaking it for the table's
capability was the actual error, compounded by not opening the insert path to check.

This produced two PRDs and a user story that all said "no confirmed data source" for the forecast
chart, which was wrong: `flood_road_values` had the data all along, unused by any query.

## How to apply

Before writing "no data source" or "would need a new table/endpoint" into a PRD's Risks section,
find the function that writes rows into the candidate table (not just the function that reads it
today) and read its loop structure. A `WHERE column = single_value` in existing query code is
evidence about that query's current need, not evidence about what the column or table holds across
all its rows. This applies whenever a table's own description ("keyed by X") could mean either "one
row per X" or "many rows spanning X," since both read the same in a one-line schema summary.

## Source blockers

- None. This surfaced from a PRD risk-assessment gap, not a resolved blocker. No blocker page
  exists for it.

## Status history

- **2026-09-23, active.** Captured after the user asked "what about flood_road_values?" and a
  schema and write-path check (`create_geojson_tables.py`, `geojson_to_pg.py`) showed the table
  already had the forecast chart's data, reversing the "no data source" conclusion in
  [[PRD-001-flood-routing-mockup-frontend-gap|flood-routing-mockup-frontend-gap]], [[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]], and
  [[US-001-depth-forecast-chart|depth-forecast-chart]].
