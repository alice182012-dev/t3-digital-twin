---
date_drafted: 2026-10-07
type: user-story
us_id: "US-086"
story_label: "1"
epic: "[[EP-12-core-output-hygiene]]"
status: Reviewed
priority: P2
estimate: S
sprint: 12
subsystem: core-output
related: ["[[EP-12-core-output-hygiene]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
title: "Prune old rows of `flood_road_values`"
---

# US-086 Prune old rows of `flood_road_values`

As the operator of the server, I want the table that routing reads to keep a fixed number of runs, so it cannot fill
the disk the way `flood_extent_polygon` did before its prune ([[US-067-prune-flood-extent-polygon-rows|prune-flood-extent-polygon-rows]]).
Given the checked state on 2026-10-07, the other core tables have a cap (`FLOOD_EXTENT_KEEP_RUNS=8` for
`flood_extent_polygon`, `EDGE_TABLE_KEEP_RUNS=3` for the edge depth files, a 48-hour retention policy on
`netcdf_values`), and `flood_road_values` has none. The only `DELETE` that touches it is in
`scripts/flood_roads/flood_on_roads.py`. It replaces the rows of one run with the same `timestamp` and
`forecast_time` before it inserts them. The older writer, `scripts/database/geojson_to_pg.py`
(`delete_old_values`), deletes the rows of one file only.
Given the table after many runs, when the prune task runs, then rows older than the newest N runs are gone, the rows
of the newest N runs are untouched, and a test with a table of N + 2 runs shows exactly N left. The task runs in
`routing_adapter` after `flood_on_roads`, and it takes N from a new variable with a default that the story sets after
it reads the real row count and size on the server.
Read the size first. Measure the row count, the table size, and the rows per run on the server, and record them in
[[core-output-contract]] before choosing N. The contract page already lists this table as having no retention.
Priority: P2. Status: Reviewed. Estimate: S. Sprint: 12. Dependencies: `US-073` (the task goes into
`routing_adapter`), done as `Reviewed` on `modular`, and `US-094` (the archive of D-016 must work before the 24-hour prune runs). The size reading is better after the storm replay of `US-089`,
because a replay writes many runs quickly.
Evidence: None yet.

Revised acceptance (2026-10-08, D-017). The user chose a time-based prune: rows older than 24 hours are removed, in place of "the newest N runs". The size reading was taken on 2026-10-08: 6,955 MB, about 214,000 rows (planner estimate), 377 run timestamps since 2026-09-23, about 18 MB per run. The 24-hour rule is safe only because the raw 3Di output is archived (D-016); without the archive this table is the only depth history older than 2 days.
