---
date: 2026-09-22
type: concept
status: active
tags: [minio, airflow, flood-tile]
related: ["[[SW Architecture]]", "[[flood-extent-polygon-tiles-airflow-minio]]", "[[2026-09-18]]", "[[graphhopper-backend]]", "[[point-depth-lookup-backend]]", "[[raster-first-flood-pipeline]]"]
last_updated: 2026-09-24
---

# MinIO flood-extent tile pipeline

This pipeline turns each timestep's depth raster into vector tiles the map can draw, and writes an
audit copy of the same polygons to PostGIS. It is the source for the map's flood overlay, not for
routing; see [[graphhopper-backend]] for why those two stay on separate tables.

## Where the data lives

MinIO runs one bucket per pipeline (`compose.yml`'s `minio-init` service creates them):
`flood-results-full`, `initial-wl`, `manholes-data`, and `flood-extent`. Only `flood-extent` is set
to public, anonymous download (`mc anonymous set download`), because it is the one bucket served
straight to the browser. The MinIO API port itself stays bound to `127.0.0.1`, so that bucket is
public only through nginx's proxy, never directly.

Inside `flood-extent`, tiles land at `runs/<run_ts>/<timestep_key>/{z}/{x}/{y}.pbf`. `run_ts` is a
fixed-width `YYYYMMDDTHHMMSS` string, chosen so lexical sort order matches chronological order.
`floodmap/graphhopper-maps/nginx.conf` rewrites requests under `/flood-extent/` to
`/flood-extent/runs/...` and proxies them to MinIO on port 9000; a tile that was never cut returns
MinIO's own 404, not the single-page app's `index.html`, so the map treats a missing tile as an
empty one rather than an error.

## The Airflow task

`dags/flood_mapping_dag.py`'s `task_build_flood_tiles` (task 9 in the DAG, named
`9_build_flood_tiles`) runs after `3_calculate_depth` and `0b_ensure_schema`. It reads the run's
depth directory from task 3's XCom, takes `run_ts` from `flood_extent.run_ts_for_depth_dir` (the
`stamp_key` of the earliest `depth_*.tif`), and calls `scripts/flood_extent/publish.py`'s
`publish_run` once for the whole run.

The road-mapping chain (extract GeoJSON, merge, map roads, upload, write to Postgres) left the DAG
on 2026-09-24, per the plan [[raster-first-flood-pipeline]]. That chain wrote `flood_road_values`,
which routing reads. No DAG task writes `flood_road_values` until Story 3 of
[[raster-first-pipeline-stories]] lands, so the DAG must not be deployed before then.

`publish_run` builds and uploads one timestep at a time, `FLOOD_EXTENT_WORKERS` (default 2) of them
in parallel. If any timestep fails, `publish_run` raises without deleting tiles or rows already
published for timesteps that succeeded: a missing tile 404s and the map treats it as empty, so
partial per-run state is safe to leave in place. Bucket pruning and local cleanup only run after
every timestep in the run has succeeded.

## Filename to UTC conversion

`scripts/calculate_depth.py` writes `depth_YYYYMMDD_HHMMSS.tif` filenames in Vietnam local time
(UTC+7), not UTC. `publish.py`'s `valid_time_utc()` converts that filename time back to UTC before
writing `flood_extent_polygon.valid_time_utc`. `flood_extent_runs.py`'s `list_timesteps` converts
the stored UTC value back to local time when answering `GET /flood/timesteps`, because the MinIO
tile folder names on disk are still keyed by the original local-time string. Getting either
direction of this conversion wrong makes `GET /flood/timesteps` return a `valid_time` that does not
match any tile the frontend can actually fetch, off by exactly 7 hours.

## PostGIS audit table

Each dissolved band polygon for each timestep gets one row in `flood_extent_polygon`
(`run_ts, valid_time_utc, dn_code, area_m2, geom`), upserted on
`(run_ts, valid_time_utc, dn_code)` so a retried publish replaces its own row instead of
duplicating it. `flood_extent_runs.py` reads only this table; it never touches the tile files
directly.

## PostGIS depth raster

`flood_depth_raster` (`run_ts, valid_time_utc, rast`) holds each timestep's `depth.tif` as a PostGIS
raster, upserted on `(run_ts, valid_time_utc)`. It exists so `GET /flood/points`
([[point-depth-lookup-backend]]) can answer the exact depth at an arbitrary point, which
`flood_road_values` (per segment) and `flood_extent_polygon` (banded ranges) cannot.

The `9b_load_depth_raster` task runs beside `9_build_flood_tiles` and reads the same `run_ts` from
task 5's XCom, so both tables share one (run, valid time) key. `scripts/flood_extent/raster_load.py`
reprojects each `depth_*.tif` from EPSG:3405 to EPSG:4326 with `gdal.Warp`, then loads it with
`ST_FromGDALRaster`. The loader sets `postgis.gdal_enabled_drivers = 'GTiff'` for its session,
because PostGIS disables every GDAL driver by default and the load otherwise fails with "Could not
open bytea with GDAL". Nothing reads the table yet, and no retention job prunes it.

## Retention

`publish_run`'s `prune_bucket_runs` keeps the newest `FLOOD_EXTENT_KEEP_RUNS` runs (default 3) in
the bucket, always preserving the run currently being published, and deletes every object under
older `runs/<run>/` prefixes in batches of 1,000 keys (the `DeleteObjects` API's per-call cap).
Local scratch space (`FLOOD_EXTENT_WORK_DIR`, plus the depth directory itself) is separately swept
by `cleanup_old_files`, which deletes any top-level child older than
`FLOOD_EXTENT_CLEANUP_MAX_AGE_HOURS` (default 24), using each child's newest file's mtime as its
age so a folder still being written is never mistaken for a stale one.

## How the frontend picks a timestep

`floodmap/graphhopper-maps/src/floodmap/FloodStore.ts` sets `FRESH_DATA_WINDOW_MS` to 45 minutes.
The map shows the flood layer only when the closest available timestep to now falls within that
window; otherwise it falls back to the plain map. `useFloodBootstrap` re-fetches the timestep list
well under that window so the map picks up a new run promptly.

## Open items

- `artifacts/docs/claude-plan/flood-extent-polygon-tiles-airflow-minio.md` is the plan this
  pipeline was built from; the parts already shipped (per-timestep tiles, MinIO storage, the
  45-minute freshness window, the timezone conversion) are described above as built. Check that
  plan file's own status before assuming anything past what this page states is still open.
- GRASS GIS still runs the raster-to-polygon step inside `flood_extent.py`; no GRASS-free rewrite
  is planned.
