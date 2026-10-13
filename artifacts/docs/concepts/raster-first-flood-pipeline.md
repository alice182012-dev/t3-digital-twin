---
date: 2026-09-24
type: concept
status: active
tags: [concept, airflow, postgis, raster, routing, timescaledb]
related: ["[[EP-06-raster-first-pipeline|raster-first-pipeline-stories]]", "[[SP-01-prd-and-backlog|sprint-plan]]", "[[flood-extent-polygon-tiles-airflow-minio]]", "[[minio-flood-extent-pipeline]]", "[[3di-simulation-orchestration]]", "[[BL-003-airflow-cannot-import-flood-utils|airflow-cannot-import-flood-utils]]", "[[EP-04-timescaledb-and-flood-metrics|timescaledb-and-flood-metrics]]"]
last_updated: 2026-10-13
---

# Raster-first flood pipeline

This page is the plan of 2026-09-24. The sampler that it describes (`flood_on_roads`, `road_segment`, and `flood_road_values`) was deleted on 2026-10-13 ([[US-123-delete-flood-on-roads-and-flood-road-values|US-123]], [[decision-log|D-038]]), and the edge depth table replaced it. Read the page as history.

Replace the GeoJSON chain in `dags/flood_mapping_dag.py` with tasks that read the depth rasters
directly, the way `dags/flood_forecast_state_test_dag.py` already does for tiles.

## Decisions from the user

- Tasks `4_extract_geojson_full`, `5_merge_geojson`, and `6_mapping_geojson` go. Tasks
  `7_upload_minio` and `8_upload_postgres` go with them, since they have no input once 6 is gone.
- The depth raster in PostGIS is the source of truth.
- The DAG needs these tasks: load the raster into PostGIS, compute flood on roads for routing,
  compute flood on points for the frontend, build the flood tiles, and compute the data for
  TimescaleDB. The routing engine is GraphHopper.
- `run_ts` comes from `flood_extent.stamp_key` of the earliest depth file, as in the test DAG.
  Checked: it equals what the merge task derived, in the same `YYYYMMDDTHHMMSS` format.

## Decisions from the user, 2026-09-24 (Stage B)

1. **Write in place.** The flood-on-roads task writes `flood_road_values`, so routing code and the table's
   contract do not change. A shadow table is used only for the comparison.
2. **Mean depth per road piece.** (Superseded on 2026-09-25 by D-006: `depth` is the maximum, and there is no
   `depth_max` column. The reasoning below is kept as the record.) The vault records "mean" or "average" only for the route chart's
   route-level average. The old pipeline did no averaging: it cut each road by the 1 m flood cells, so each
   row carried one cell's depth. Mean over a 50 m piece can hide a short deep spot (5 m at 0.6 m depth over a
   mostly dry piece averages about 0.06 m, under the motorbike's 0.2 m limit). The new rows therefore also
   store the piece's maximum depth, and the comparison counts pieces whose passability changes under mean
   against the old rows and against maximum.
3. **Retire `dags/test_dag.py`.** It is a live DAG that imports the retired scripts.
4. **Remove the `flood-results-full` bucket.** Remove it from `minio-init`, compose, the README, and the tests
   now. Delete the bucket and its 13 objects (12 MB) on the server at the Stage B deploy, after the DAG stops
   referencing it (the old task `7_upload_minio` would otherwise recreate it).

Each decision, with its reason and alternatives, is also in [[decision-log]].

Work for Stage B happens on the local branch `stage-b`, which holds the merged DAG retirement, so that
`flood-on-points` stays safe to push.

## Design points agreed in discussion

- **Flood on points is not a DAG task.** `GET /flood/points` reads the raster per request. A
  precomputed grid is only worth building if the latency check fails.
- **GraphHopper does not read flood data.** `floodmap-backend` turns `flood_road_values` into a
  `custom_model` per request. The roads task feeds that table.
- **Roads need a stable segment ID.** The roads file (`toa-do-duong-hanoi.geojson`, 8.4 MB, 12,431
  `LineString` features) already gives every way a unique OSM id in `@id`, for example
  `way/11835354`. The old mapping step lost it. A `road_segment` table keeps it.
- **Build before deleting.** The new roads task writes a shadow table, and its output is compared
  with `flood_road_values` for one real run before any old task is removed.
- **Store the raster as tiles.** A whole timestep is 10077 by 5436 pixels, 209 MB decoded in memory
  (the `.tif` is 22 MB, the stored PostGIS value 26 MB, and about 5 MB per timestep for a typical
  run). A lookup on the whole raster took 80 to 280 ms, so each lookup unpacks the full value. Tiles
  with a spatial index should touch one tile. Storage is not the concern, memory and latency are.

## Target DAG

```
0_check_forecast_rain > 1_trigger_simulation > 2_download_results > 3_calculate_depth
3_calculate_depth > load_depth_raster (tiles, retention)
load_depth_raster > flood_on_roads > flood_metrics (TimescaleDB)
3_calculate_depth > build_flood_tiles (reads the tifs directly, parallel)
2_download_results > 3b_upload_netcdf_postgres (unchanged, after a schema fix)
```

## Phases

1. **Foundations, in parallel.** A: tiled raster load, the `GET /flood/points` query on tiles, and
   retention. B: the `road_segment` table and loader. They share no files.
2. **Flood on roads.** A SQL task that samples the tiled raster along each `road_segment` piece and
   writes a shadow table shaped like `flood_road_values`. Compare it with the old output for one run.
3. **Switch and retire.** Point routing at the new table, rewrite the DAG (remove 4 to 8, `run_ts`
   from `stamp_key`), and delete the unused scripts and tests.
4. **TimescaleDB data.** Mount `flood_utils.py` for Airflow, key the extractor by `segment_id`, and
   load the extractor's output.

## Throughput checkpoint

- **Blocking first steps.** Real inputs for the delegates (done: `marie-curie/raster-first/`), and
  the story files.
- **Independent workstreams.** Phase 1 A and B touch disjoint files.
- **Shared mutable state.** `flood_depth_raster` (A owns it) and `flood_road_values` (untouched until
  Phase 3). Phase 2 waits for both A and B.
- **Smallest safe decomposition.** One owner per workstream, each in its own worktree.

## Deploy order

- Run `create_flood_depth_raster_tables.py` before the backend that reads `flood_depth_raster_tile`
  starts. Without the table the endpoint errors, and `0b_ensure_schema` only creates it on the next
  DAG run.
- Until the next `9b` run loads tiles, `GET /flood/points` returns 404 for every timestep.
- `flood_depth_raster` (whole rasters) has no reader or writer after this change. Drop it in Phase 3.
- After the Stage B backend runs on tiles, drop the legacy whole-raster table on `storage-postgres`:
  `DROP TABLE IF EXISTS flood_depth_raster;`. Delete the `flood-results-full` bucket and its 13 objects
  (12 MB) at the same deploy, after the DAG stops referencing it.
- `server.py` opens a new connection per request, and the first raster call in a connection loads the
  PostGIS raster library (57 ms locally against 1.4 ms for a plain connect). Reuse connections when
  the latency check runs.

## Stage B deploy order

1. Keep `flood_mapping_full` paused. Push `stage-b`, then on the server run `git fetch; git checkout stage-b; git pull`.
2. Run the schema scripts in `airflow-worker`: `create_flood_road_tables.py` (adds `segment_id`; renamed from `create_geojson_tables.py` on 2026-09-25),
   `create_road_segment_table.py`, and `create_flood_depth_raster_tables.py` (tile table only). With D-006,
   routing reads plain `depth`, so the backend no longer needs a new column before it is rebuilt.
3. Load the roads once with `load_road_segments`, then check the piece count (35,652 expected).
4. Rebuild `floodmap-backend` from the Mac (`docker compose build`) and recreate it on the server with
   `--no-deps`.
5. Verify `flood_on_roads` on a real run into a shadow table first, not into `flood_road_values`: writing in
   place replaces the old rows of that run.
6. Delete the `flood-results-full` bucket (13 objects) and drop `flood_depth_raster`, after the DAG no longer
   references them.
7. Unpause the DAG and watch one full cycle. The rain gate skips a dry cycle, so a full cycle needs rain, or the
   tasks are run by hand on a real run.
8. Take the evidence screenshots (including a graded route built from the new rows), then mark the stories `Done`.

## Review findings that shape the plan (2026-09-24)

- **`3b_upload_netcdf_postgres` fails when `netcdf_files` is missing.** The table is missing on the
  server, and `create_netcdf_tables.py` is not called by any DAG. The latest run failed only on this
  task, so it was marked `failed` although every other task succeeded. Fix in `task_ensure_schema` (Phase 3).
- **A real cycle is running.** Run `20260924T163700` loaded 4 timesteps into `flood_depth_raster` (21 MB
  stored), so the raster load works in production. Do not edit task ids in the DAG while a run is in
  progress.
- **The `vi` locale bug is deferred.** Place search is broken on the live UI, tracked in
  [[BL-008-photon-rejects-vi-locale|photon-rejects-vi-locale]].

## Status

- **2026-09-24.** Plan written. Phase 1 starting.
- **2026-09-24.** No push until `flood_mapping_full` is ready to deploy, at the user's request. Commit
  locally, and do not update PR #1 before then.
- **2026-09-24.** Story 1 (`road_segment`) merged locally and `Reviewed`. It cuts ways into equal pieces of
  at most 50 m (35,652 pieces from 12,431 ways). Story 2 (tiles) and the DAG retirement are in progress.
- **2026-09-24.** Story 2 (tiles) merged locally and `Reviewed`. Lookup 69 ms to 0.2 ms warm on a local
  PostGIS. The DAG retirement is in progress.
- **2026-09-24.** Stage A deployed to the server at `6155f09` (everything except the DAG retirement). The
  backend and frontend images were built from the Mac (`docker compose build`), because Docker's
  credential helper fails in an SSH session on the server, and the containers were recreated on the
  server with `--no-deps`. `flood_mapping_full` was already paused and stays paused. Tiles for run
  `20260924T153638` were loaded by hand. The next steps are Story 3 (flood on roads) and Story 4.
- **2026-09-24.** Stage B decisions recorded. Branch `stage-b` created with the DAG retirement merged. Two
  delegates started: flood on roads (Story 3) and Story 4 preparation (test DAG, bucket, legacy table).
- **2026-09-24.** Story 4 preparation is done on `stage-b`, in three commits (`4c1329f`, `d60179f`, `5e50ceb`):
  `dags/test_dag.py` (DAG `flood_forecast_pipeline_test`) deleted; the `flood-results-full` bucket removed from
  `compose.yml`, `.env.example`, the README, and the MinIO concept page; `create_flood_depth_raster_tables.py`
  creates only `flood_depth_raster_tile`. The server bucket, its objects, and the old table stay until the
  Stage B deploy. Leftovers for the final cleanup: `scripts/merge_to_minio.py` was dead code, and it was deleted on 2026-10-13
  (`scripts/mapping/*` went on 2026-09-29); the docstring at `dags/flood_mapping_dag.py:205` still names
  `flood_depth_raster`; `artifacts/raw/T3-Digital-Twin_Architecture.md` (read-only) still lists the bucket
  at lines 94 and 271, for the user to update.
- **2026-09-24.** Story 3 merged into `stage-b` and `Reviewed`. Findings: the server runs `SAMPLE_RATE=20`, so old
  `flood_road_values` depths come from one pixel per 20 m cell and half of the old wet slivers are dry along the
  road. Mean depth per piece misses 39 to 168 real closures per vehicle and run, and maximum depth misses 0 to 5 (9 in total, all beside a piece boundary).
  The server's PostgreSQL `TimeZone` is `Etc/UTC`, so the local-time alignment holds. Open decision: routing's
  band filter on `depth_max`.
- **2026-09-25.** Created [[decision-log]] with the Stage B decisions and D-005: routing filters on `depth_max`.
- **2026-09-25.** Built on `stage-b` and merged: `flood_on_roads` and road loader tasks in the DAG (`e397153`,
  `c39bffb`), routing on `depth_max` (`e6b51e8`, `191e33b`, decision D-005). The DAG loads in a real `DagBag` on the
  server (11 tasks, 15 edges). Next: the Stage B deploy order above.
- **2026-09-25.** D-006: depth per road piece is the maximum, stored in `depth`. Supersedes D-002 and D-005, drops the
  `depth_max` column, and removes the schema-first deploy hazard. Code change in progress on `stage-b`.
- **2026-09-25.** D-006 code merged into `stage-b` (`ad328a4`, `e258620`, `87271e8`, `71eba9a`, `d31f198`): `depth` is the deepest
  1 m sample, the `depth_max` column is gone, and routing reads plain `depth`. All tests pass on the merged tree. Next: the
  Stage B deploy order.
- **2026-09-25.** Renamed `create_geojson_tables.py` to `create_flood_road_tables.py` on `stage-b` (`7916abd`), because it creates the routing
  tables and has nothing to do with GeoJSON now. The old scripts under `scripts/mapping/` stay until the server verification.
- **2026-09-25, Stage B on the server.** Deployed `stage-b` (`2be63a4`) with the DAG still paused, and did steps 1 to 4. Airflow parses the
  real DAG folder with no import errors and exactly 11 tasks. The three schema scripts and `create_netcdf_tables` ran (twice each,
  idempotent), `segment_id` was added to `flood_road_values`, and its 25,036 rows are untouched. `road_segment` holds 35,652 pieces
  from 12,431 ways with a worst length error of 0 m, and a second load changed nothing. For run `20260924T164803`, tiles loaded in
  55.8 s and `flood_on_roads` wrote 8,444 rows into `flood_road_values_shadow` in 18.8 s, identical to the local result. No backend
  rebuild was needed. Left in place on the server: the shadow table and one registry row (`flood_road_file` id 8,
  `flood_on_roads_20260924T164803`). Not done, and waiting for the user: delete the `flood-results-full` bucket, drop
  `flood_depth_raster`, write in place, unpause, and a full cycle with a graded route.
- **2026-09-25, Stage B, irreversible steps done on the server (user-approved).** Deleted the `flood-results-full` bucket (15 objects, 14.7 MB;
  the earlier count of 13 had grown) and dropped `flood_depth_raster` (13 rasters, 122 MB, no dependents). Two of its runs (`163700`,
  `170000`) had never been tiled, so their point depths are gone. Wrote `flood_on_roads` in place for run `20260924T164803`: 8,444 rows
  replaced 7,620, and the table total is 25,860 as computed. Routing on the new rows detours around flooded pieces. A full cycle is
  next, using `flood_forecast_consecutive_state_test` because it is not raining (see D-007 in [[decision-log]]).
- **2026-09-25, state-test DAG.** `flood_forecast_consecutive_state_test` now follows the production steps for both events (`6ddfb31`, `bc9032d`,
  `5ef7f2a`, merged into `stage-b` at `052fb42`, pushed as `a95d07f`): schema, road loader, tiles, raster load, and flood on roads for each
  event, all under event 1's run name (D-007), with no netcdf upload. `raster_load.load_run` gained `keep_runs`, so a test run cannot prune real
  runs. Loaded in a real `DagBag` on the server: 14 tasks, 22 edges, no import errors, no schedule. Not yet triggered: a run costs two 3Di
  simulations. The page opens in flood mode by the demo default, so the test event shows without a manual switch.

