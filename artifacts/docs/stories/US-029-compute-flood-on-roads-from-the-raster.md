---
date_drafted: 2026-09-24
type: user-story
us_id: "US-029"
story_label: "3"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Done
priority: P0
estimate: L
sprint: 2
subsystem: airflow-pipeline
related: ["[[EP-06-raster-first-pipeline]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Compute flood on roads from the raster into a shadow table"
---

# US-029 Compute flood on roads from the raster into a shadow table

As the routing backend, I want each road piece's depth per timestep computed from the raster in
PostGIS, so routing no longer depends on the lossy GeoJSON chain.
Given a run loaded as tiles and `road_segment` loaded, when the task runs, then a shadow table
shaped like `flood_road_values` holds one row per piece per timestep, and for one real run its
values match the old `flood_road_values` rows, or each difference is explained (the old rows are
subsampled).
Depth per piece is the deepest 1 m sample along the piece, stored in `depth` (decision D-006, which
supersedes the mean and `depth_max`). The task writes `flood_road_values` in place.
Priority: P0. Status: Done. Estimate: L. Sprint: 2. Dependencies: Story 1, Story 2.
Evidence: ![[flood-on-roads-server-check.png|420]]
Details:
1. What: a task that computes each road piece's flood depth from the raster tiles into `flood_road_values`. `depth` is the deepest 1 m sample (D-006).
2. How: `flood_on_roads.compute` samples every metre along each piece that touches a wet tile, reads the wet pixels once per tile, and writes one row per piece per timestep in one transaction.
3. Why: the old chain sampled one pixel per 20 m cell on the server (`SAMPLE_RATE=20`), so about half of its wet slivers are dry along the road.
4. Effect: on the server (2026-09-25), run `20260924T164803` wrote 8,444 rows into a shadow table in 18.8 s, identical to the local result in rows, wet pieces, and depth sums, while the real table stayed untouched. Routing, the extractor, and the metrics read the same `depth`. Writing in place and a full cycle remain in Story 4.
