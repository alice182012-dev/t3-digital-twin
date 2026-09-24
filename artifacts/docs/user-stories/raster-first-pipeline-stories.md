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
  Priority: P0. Status: Reviewed. Estimate: M. Sprint: 2. Dependencies: None.
  Details:
  1. What: a `road_segment` table with one row per road piece, keyed by `segment_id` such as `way/11835354#0`.
  2. How: `load_road_segments.py` cuts each of the 12,431 ways into equal pieces of at most 50 m in EPSG:3405 and upserts them in one transaction, so a second load changes nothing.
  3. Why: routing data, TimescaleDB, and the route-forecast query need one stable road ID, and the old mapping step dropped the OSM id.
  4. Effect: unblocks Stories 3 and 4 and the TimescaleDB key change. Checked only on a local PostGIS with the real roads file: 35,652 pieces, worst length error under 1e-5 m. Not run on the server. IDs shift if the roads file or the piece length changes.

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
  Depth per piece is the mean over samples along the piece (dry samples count as 0), with the maximum stored
  beside it in `depth_max`. The task writes `flood_road_values` in place.
  Priority: P0. Status: Not started. Estimate: L. Sprint: 2. Dependencies: Story 1, Story 2.

- **Story 4: Switch routing to the new task and retire the GeoJSON tasks.**
  As a maintainer, I want tasks 4 to 8 gone and routing reading the new table, so the DAG has one
  path from depth rasters to routing data.
  Given the shadow comparison passes, when the DAG is rewritten, then tasks 4 to 8 no longer exist,
  `run_ts` comes from `flood_extent.stamp_key`, a full cycle succeeds on the server, and a graded
  `POST /route` returns a route built from the new table.
  Priority: P0. Status: Not started. Estimate: M. Sprint: 2. Dependencies: Story 3.

- **Story 5: Create the netcdf table in the schema task.**
  As an operator, I want `3b_upload_netcdf_postgres` to stop failing, so a run is not marked
  `failed` when every other task succeeded.
  Given a database without `netcdf_files`, when `0b_ensure_schema` runs, then the table exists and
  task 3b succeeds.
  Priority: P2. Status: Not started. Estimate: S. Sprint: 2. Dependencies: None.

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

