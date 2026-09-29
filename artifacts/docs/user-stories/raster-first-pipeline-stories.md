---
date_drafted: 2026-09-24
type: user-story
status: draft
subsystem: airflow-pipeline
source_ideas: []
related: ["[[sprint-plan]]", "[[raster-first-flood-pipeline]]", "[[point-depth-lookup-backend]]", "[[timescaledb-and-flood-metrics]]", "[[route-forecast-query]]", "[[airflow-cannot-import-flood-utils]]"]
tags: [user-story, epic, airflow, postgis, raster, sprint-2]
---

# Epic: raster-first flood pipeline

Replaces the GeoJSON chain (tasks `4_extract_geojson_full` to `8_upload_postgres`) in
`dags/flood_mapping_dag.py` with tasks that read the depth rasters directly. The design and the
order of work are in the plan [[raster-first-flood-pipeline]]. Rows carry Priority, Status,
Estimate, and Sprint per the vault's sprint-delegation convention.

- **Story 1: Load the roads into PostGIS with a stable segment ID.**
  As a pipeline engineer, I want the roads in a `road_segment` table keyed by a stable ID, so
  routing data, TimescaleDB, and the route-forecast query all refer to the same road pieces.
  Given `toa-do-duong-hanoi.geojson` (12,431 ways, each with a unique OSM id in `@id`), when the
  loader runs twice, then `road_segment` holds the same `segment_id` values both times, every way
  is present, and the pieces of each way add up to that way's length within 0.5 m.
  Priority: P0. Status: Done. Estimate: M. Sprint: 2. Dependencies: None.
  Evidence: ![[road-segment-server-check.png|420]]
  Details:
  1. What: a `road_segment` table with one row per road piece, keyed by `segment_id` such as `way/11835354#0`.
  2. How: `load_road_segments.py` cuts each of the 12,431 ways into equal pieces of at most 50 m in EPSG:3405 and upserts them in one transaction.
  3. Why: routing data, TimescaleDB, and the route-forecast query need one stable road ID, and the old mapping step dropped the OSM id.
  4. Effect: it feeds the DAG tasks and the TimescaleDB key change. On the server (2026-09-25): 35,652 pieces, every way present, worst length error 0.000000000 m, and a second load changed nothing. IDs shift if the roads file or the piece length changes.

- **Story 2: Store depth rasters as tiles and read them through a spatial index.**
  As the point-depth endpoint, I want each timestep stored as tiles, so a lookup touches one tile
  instead of unpacking a 209 MB raster, and old runs are removed.
  Given the real `depth_20260924_170639.tif`, when it is loaded as tiles, then `ST_Value` at three
  points matches `gdallocationinfo`, a lookup on the server is faster than the current 80 to 280 ms,
  and only the newest runs are kept (default 3).
  Priority: P0. Status: Reviewed. Estimate: M. Sprint: 2. Dependencies: None.
  Evidence: ![[raster-tiles-server-check.png|420]]
  Details:
  1. What: each timestep's depth raster is stored as 256 by 256 tiles in `flood_depth_raster_tile`, read through a spatial index, and runs older than the newest 3 are pruned.
  2. How: `load_run` reprojects to EPSG:4326 and cuts tiles with `ST_Tile` in one delete-and-insert transaction. `GET /flood/points` selects the tile under the point, then runs `ST_Value`.
  3. Why: the whole-raster lookup unpacked 209 MB per request and took 80 to 280 ms on the server.
  4. Effect: deployed on 2026-09-24 (commit `6155f09`). On the server a tile lookup takes a median of 0.56 ms in the database, and a full request about 81 ms, because each request opens a new connection ([[flood-points-connection-per-request]]). Retention has not run on the server, since only one run has tiles, so the story stays `Reviewed`.

- **Story 3: Compute flood on roads from the raster into a shadow table.**
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

- **Story 4: Switch routing to the new task and retire the GeoJSON tasks.**
  As a maintainer, I want tasks 4 to 8 gone and routing reading the new table, so the DAG has one
  path from depth rasters to routing data.
  Given the shadow comparison passes, when the DAG is rewritten, then tasks 4 to 8 no longer exist,
  `run_ts` comes from `flood_extent.stamp_key`, a full cycle succeeds on the server, and a graded
  `POST /route` returns a route built from the new table.
  Priority: P0. Status: In progress. Estimate: M. Sprint: 2. Dependencies: Story 3.
  Evidence: ![[graded-routing-server-check.png|420]]
  Details:
  1. What: the DAG no longer builds GeoJSON. It loads roads and computes flood on roads into `flood_road_values`, the table routing reads.
  2. How: `stage-b` removes tasks 4 to 8, `dags/test_dag.py`, and the `flood-results-full` configuration, and adds the `load_road_segments` and `flood_on_roads` tasks. On the server the bucket (15 objects, 14.7 MB) and the old `flood_depth_raster` table (122 MB) were deleted, and `flood_on_roads` was written in place for run `20260924T164803`.
  3. Why: one path from the depth rasters to routing, with the raster as the source of truth.
  4. Effect: routing now reads the new rows. Graded routes detour around flooded pieces (for example 111 m becomes 6,262 m around a 2.76 m piece), and two test routes have no connection once the flood applies. Still open: a full DAG cycle, the frontend on a live event (the state-test DAG will provide one, see D-007), and dropping the `flood_road_values_shadow` table left on the server from Story 3's comparison run. The old scripts are deleted (2026-09-29).

- **Story 5: Create the netcdf table in the schema task.**
  As an operator, I want `3b_upload_netcdf_postgres` to stop failing, so a run is not marked
  `failed` when every other task succeeded.
  Given a database without `netcdf_files`, when `0b_ensure_schema` runs, then the table exists and
  task 3b succeeds.
  Priority: P2. Status: Reviewed. Estimate: S. Sprint: 2. Dependencies: None.
  Details:
  1. What: the netcdf tables are created by the schema task.
  2. How: `task_ensure_schema` calls `create_netcdf_tables.create_tables()`, which is idempotent.
  3. Why: `3b_upload_netcdf_postgres` failed with `relation "netcdf_files" does not exist`, which marked every run `failed`.
  4. Effect: on the server the three netcdf tables now exist, created by hand on 2026-09-25 with the same function (run twice). The story stays `Reviewed` until a real cycle shows task 3b succeeding.

## Status history

- **2026-09-24, draft.** Drafted from the plan [[raster-first-flood-pipeline]] after the user chose to
  retire the GeoJSON tasks. All five stories go in Sprint 2, since [[route-forecast-query]] and
  [[timescaledb-and-flood-metrics]]'s Story 4 need the segment ID and the new roads table.
- **2026-09-24, draft.** Story 1 built and reviewed (`ff18140`, `fcc4a03`, `23fad9c`, merged). Status is
  `Reviewed`: it passed on a local PostGIS with the real roads file, and has not run on the server.
- **2026-09-24, draft.** Story 2 built and reviewed (`b239491`, `1238616`, `bc158e5`, `876cbe5`, merged).
  Status is `Reviewed`: the numbers come from a local PostGIS, and none is measured on the server.
- **2026-09-24, draft.** Story 2 deployed to the server (commit `6155f09`) and checked there: 4 timesteps of
  880 tiles, values equal to the earlier `gdallocationinfo` reference, tile lookup median 0.56 ms.
  Still `Reviewed`, because pruning needs a fourth run to show on the server.
- **2026-09-24, draft.** Decided: write `flood_road_values` in place, mean depth per piece with the maximum stored
  beside it, retire `dags/test_dag.py`, and remove the `flood-results-full` bucket. See [[raster-first-flood-pipeline]].
- **2026-09-24, draft.** Story 3 built and reviewed on `stage-b` (`55910af`, `b2387df`, `1ccddc9`, `89ac6a0`,
  `b2f04d4`). The old rows are not ground truth: every old depth equals the top-left pixel of a 20 m cell,
  because the server runs `SAMPLE_RATE=20`. Status is `Reviewed`: nothing ran on the server.
- **2026-09-25, draft.** Story 4 is `In progress` on `stage-b`. Built: the DAG retirement, the road loader and
  `flood_on_roads` tasks (11 tasks, 15 edges, loaded in a real `DagBag` on the server), the removal of
  `dags/test_dag.py` and the `flood-results-full` configuration, and routing on `depth_max` (D-005). Not done:
  the server deploy, a full cycle, a graded `POST /route` on the new rows, and deleting the old scripts.
- **2026-09-25, draft.** The user chose the maximum depth for every use (D-006). `depth` now holds the maximum and there is no
  `depth_max` column. A delegate is making the code and note changes on `stage-b`.
- **2026-09-25, draft.** Stage B checked on the server (`stage-b` at `2be63a4`). Story 1 and Story 3 are `Done`, each with
  a server screenshot. Story 5 is `Reviewed`: the netcdf tables now exist, and task 3b needs a real cycle. Story 4 stays
  `In progress`: writing in place, the bucket and old table removal, a full cycle, and a graded route remain.
- **2026-09-25, draft.** Story 4 progress on the server: deleted the `flood-results-full` bucket and `flood_depth_raster`, wrote
  `flood_on_roads` in place for run `20260924T164803` (8,444 rows replacing 7,620), and confirmed graded routing on the new rows.
  Still `In progress`: a full cycle, the frontend on a live event, and deleting the old scripts.
- **2026-09-29, draft.** Deleted the retired GeoJSON chain's source: `scripts/extract_geojson.py`,
  `scripts/mapping/extract_geojson_full.py`, `mapping_geojson.py`, `merge_geojson.py`, and
  `upload_minio.py`, plus their only two callers, `scripts/run_d1_ingest.py` and `test/test.py`
  (both local harnesses for the retired chain, confirmed unused by `dags/flood_mapping_dag.py` or
  anything else in the repo). `scripts/database/geojson_to_pg.py` stayed: `flood_on_roads.py` and
  `extract_run.py` still call it. Corrected a stale `test/test.py` reference in
  [[3di-simulation-orchestration]]. Still `In progress`: a full DAG cycle, the frontend on a live
  event, and dropping the `flood_road_values_shadow` table on the server (an operational step, not
  a code change; `flood_on_roads.py`'s `create_shadow_table` and `compare_with_old.py` stay, since
  they are live comparison tooling, not part of the retired chain).

