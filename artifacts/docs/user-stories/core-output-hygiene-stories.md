---
date_drafted: 2026-10-07
type: user-story
us_ids: ["US-086", "US-087"]
status: draft
subsystem: core-output
source_ideas: []
related: ["[[sprint-plan-3]]", "[[core-output-contract]]", "[[routing-first-consumer-stories]]", "[[flood-on-roads]]", "[[graphhopper-backend]]", "[[prune-flood-extent-polygon-rows]]", "[[2026-10-07]]"]
tags: [user-story, epic, retention, tests, sprint-12]
---

# Epic: core output hygiene

Two gaps found while building [[routing-first-consumer-stories]] on 2026-10-07. Neither blocks a build. Both are in
Sprint 12 of [[sprint-plan-3]], at the user's request. Each row carries Priority, Status, Estimate, Sprint, and
Dependencies, as an extension of the base Epic shape in [[user-story-types]]. A story reaches `Done` only with a
screenshot and numbered details, recorded here and in `sprint-plan-3.md`.

- **Story 1 (US-086): Prune old rows of `flood_road_values`.**
  As the operator of the server, I want the table that routing reads to keep a fixed number of runs, so it cannot fill
  the disk the way `flood_extent_polygon` did before its prune ([[prune-flood-extent-polygon-rows]]).
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
  Priority: P2. Status: Not started. Estimate: S. Sprint: 12. Dependencies: `US-073` (the task goes into
  `routing_adapter`), done as `Reviewed` on `modular`. The size reading is better after the storm replay of `US-089`,
  because a replay writes many runs quickly.
  Evidence: None yet.

- **Story 2 (US-087): Make `test_flood_areas.py` run without hand-set paths, and run it in CI.**
  As a maintainer, I want the routing flood-area test to run the same way everywhere, so a regression in
  `derive_areas()` and `build_custom_model()` fails a check and does not wait for someone to remember the setup.
  Given `floodmap/graphhopper-flood-road/backend/test_flood_areas.py`, when it runs without `PYTHONPATH`, then it fails
  with `ModuleNotFoundError: create_flood_road_tables`. It needs two directories on the path
  (`floodmap/graphhopper-flood-road/scripts` for `flood_utils`, and `scripts/database` for `create_flood_road_tables`)
  and a PostGIS database in `FLOOD_TEST_DSN`. With the path set and no DSN, it prints `FLOOD_TEST_DSN unset; skipping`
  and exits as a pass. The only CI workflow, `.github/workflows/java-module.yml`, never runs it.
  Checked on 2026-10-07 on the Mac with `python3 -I`: the documented path (`PYTHONPATH=../scripts:../../../scripts/database`)
  imports and skips, and a run without the path fails.
  Given the story is done, when CI runs, then a job starts a throwaway `postgis/postgis:15-3.4` service, sets the path
  and `FLOOD_TEST_DSN`, and runs the test to a real pass. A test that skips in CI fails the job. The docstring shows one
  command that works from the repository root.
  The earlier log line said the test "failed at `5e4a314` already". The cause is the missing path, not a change to the
  code under test, so check that the test body passes against a real PostGIS before the story closes.
  Priority: P3. Status: Not started. Estimate: S. Sprint: 12. Dependencies: None. CI needs the repository's GitHub
  Actions, which `java-module.yml` already uses.
  Evidence: None yet.

## Status history

- **2026-10-07, draft.** Written at the user's request, from findings 1 and 4 of the log of [[2026-10-07]]. Both
  findings were rechecked against the code before the stories were written. Finding 1 holds: no age-based prune
  exists. Finding 4 is narrower than logged: the test imports with the documented path and skips without a database.
  The next free ID was `US-086`.
