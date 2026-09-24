---
date: 2026-09-24
type: plan
status: active
tags: [plan, airflow, postgis, raster, routing, timescaledb]
related: ["[[raster-first-pipeline-stories]]", "[[sprint-plan]]", "[[flood-extent-polygon-tiles-airflow-minio]]", "[[minio-flood-extent-pipeline]]", "[[3di-simulation-orchestration]]", "[[airflow-cannot-import-flood-utils]]", "[[timescaledb-and-flood-metrics]]"]
---

# Raster-first flood pipeline

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
- `server.py` opens a new connection per request, and the first raster call in a connection loads the
  PostGIS raster library (57 ms locally against 1.4 ms for a plain connect). Reuse connections when
  the latency check runs.

## Review findings that shape the plan (2026-09-24)

- **`3b_upload_netcdf_postgres` fails when `netcdf_files` is missing.** The table is missing on the
  server, and `create_netcdf_tables.py` is not called by any DAG. The latest run failed only on this
  task, so it was marked `failed` although every other task succeeded. Fix in `task_ensure_schema` (Phase 3).
- **A real cycle is running.** Run `20260924T163700` loaded 4 timesteps into `flood_depth_raster` (21 MB
  stored), so the raster load works in production. Do not edit task ids in the DAG while a run is in
  progress.
- **The `vi` locale bug is deferred.** Place search is broken on the live UI, tracked in
  [[photon-rejects-vi-locale]].

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

