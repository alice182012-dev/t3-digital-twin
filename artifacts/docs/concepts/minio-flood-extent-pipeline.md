---
date: 2026-09-22
type: concept
status: active
tags: [minio, airflow, flood-tile]
related: ["[[T3-Digital-Twin_Architecture]]", "[[flood-extent-polygon-tiles-airflow-minio]]", "[[2026-09-18]]", "[[graphhopper-backend]]", "[[point-depth-lookup-backend]]", "[[raster-first-flood-pipeline]]", "[[flood-on-roads]]", "[[decision-log]]"]
last_updated: 2026-10-02
---

# MinIO flood-extent tile pipeline

This pipeline turns each timestep's depth raster into vector tiles the map can draw, and writes an
audit copy of the same polygons to PostGIS. It is the source for the map's flood overlay, not for
routing; see [[graphhopper-backend]] for why those two stay on separate tables.

## Where the data lives

MinIO runs one bucket per pipeline (`compose.yml`'s `minio-init` service creates them):
`initial-wl`, `manholes-data`, and `flood-extent`. Only `flood-extent` is set
to public, anonymous download (`mc anonymous set download`), because it is the one bucket served
straight to the browser. The MinIO API port itself stays bound to `127.0.0.1`, so that bucket is
public only through nginx's proxy, never directly.

A fourth bucket, `flood-results-full`, held the GeoJSON of the retired road-mapping chain.
`compose.yml` stopped creating it on 2026-09-24. The bucket and its objects on the server go at
the Stage B deploy of [[raster-first-flood-pipeline]]. `scripts/mapping/upload_minio.py`,
`scripts/mapping/merge_geojson.py`, and `scripts/database/geojson_to_pg.py` still default to that
bucket name until they are deleted after the flood-on-roads comparison.

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
which routing reads. Since 2026-09-25 the `flood_on_roads` task writes that table instead, from the
tiles that `9b_load_depth_raster` loads. See [[flood-on-roads]].

`publish_run` builds and uploads one timestep at a time, `FLOOD_EXTENT_WORKERS` (default 2) of them
in parallel. If any timestep fails, `publish_run` raises without deleting tiles or rows already
published for timesteps that succeeded: a missing tile 404s and the map treats it as empty, so
partial per-run state is safe to leave in place. Bucket pruning and local cleanup only run after
every timestep in the run has succeeded.

## Where the tile build spends its time

Stage times of one timestep on a grown storm (2026-10-01, step 1 of the 20:15 run): reclassify 4.5 s,
close bands 30.8 s, polygonize 67.1 s, dissolve 440.7 s, clean 4.8 s, cut tiles 70.2 s. The dissolve was a
single-threaded `ST_Union` per band group. It now runs one `ogr2ogr` per band code in parallel
(`Pipeline.dissolve_band`, `1607484`) and merges the parts. It stays `ST_Union` because
`gdal_polygonize -8` leaves overlapping polygons within a band: `ST_Collect` gave 2 to 7 percent larger
areas, and `ST_UnaryUnion` was not faster. On the same file the area per band and the tile count (190)
are identical to the old query. A timestep has about 192 tiles at zoom 10 to 16, and only the first
`FLOOD_EXTENT_TILE_STEPS` timesteps (2) of a run get tiles. The tile build grows with the flooded area:
under a sustained 50 mm/h test storm it grew from 4.4 to 6.1 minutes over the first hour after a cold
start.

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

`flood_depth_raster_tile` (`run_ts, valid_time_utc, tile_x, tile_y, rast`) holds each timestep's
`depth.tif` as 256 x 256 pixel PostGIS raster tiles. Its primary key is
`(run_ts, valid_time_utc, tile_y, tile_x)`, and a GIST index covers `ST_ConvexHull(rast)`. The table
exists so `GET /flood/points` ([[point-depth-lookup-backend]]) can answer the exact depth at an
arbitrary point, which `flood_road_values` (per segment) and `flood_extent_polygon` (banded ranges)
cannot. `scripts/database/create_flood_depth_raster_tables.py` creates it, and running that script
twice is safe.

The `9b_load_depth_raster` task runs beside `9_build_flood_tiles` and takes the same `run_ts` from
`flood_extent.run_ts_for_depth_dir`, so both tables share one (run, valid time) key. The
`flood_on_roads` task runs after `9b_load_depth_raster` and samples these tiles under the same
`run_ts`. `raster_load.load_run` reprojects
each `depth_*.tif` from EPSG:3405 to EPSG:4326 with `gdal.Warp`. Then it uploads the GeoTIFF once,
and PostGIS cuts it with `ST_Tile` inside the same `INSERT`. For each timestep the loader deletes
that timestep's tiles and inserts the new ones in one transaction, so a retried load ends with the
same rows as a clean one. The loader sets `postgis.gdal_enabled_drivers = 'GTiff'` for its session,
because PostGIS disables every GDAL driver by default and the load otherwise fails with "Could not
open bytea with GDAL".

### Why tiles

A whole timestep of the real grid is about 10,000 x 5,500 pixels, 209 MB once decoded. The first
version stored it as one row in `flood_depth_raster`, and `ST_Value` on that row decodes the whole
value for every lookup. With tiles, the lookup selects the tile under the point through the GIST
index and decodes 256 KB. Storage barely changes. The real `depth_20260924_170639.tif` (22 MB) takes
26 MB stored as 880 tiles and 27 MB as one row.

The tile size came from loading that file at four sizes into a local PostGIS 3.6.4 on PostgreSQL 18
and timing a bare `ST_Value` at six points. The endpoint's own query also reads
`ST_BandNoDataValue`, which roughly doubles the one-row time (see [[graphhopper-backend]]). "Evicted" means the table, its TOAST data, and its indexes were
evicted from `shared_buffers` first. The operating system cache stayed warm.

| Tile size | Tiles per timestep | Warm lookup, median | Evicted lookup, median |
|---|---|---|---|
| One row, no tiles | 1 | 34.9 ms | 62.1 ms |
| 64 x 64 | 13,430 | 0.13 ms | 0.9 ms |
| 128 x 128 | 3,397 | 0.11 ms | 0.7 ms |
| 256 x 256 | 880 | 0.15 ms | 0.8 ms |
| 512 x 512 | 220 | 0.31 ms | 1.0 ms |

128 and 256 tie on lookup time. The loader uses 256 because it writes a quarter of the rows, which
keeps the index and the per-timestep delete smaller.

### Why a new table

The tile table sits next to `flood_depth_raster` instead of replacing its columns. The old table's
`UNIQUE (run_ts, valid_time_utc)` allows one row per timestep, and the old loader's
`ON CONFLICT (run_ts, valid_time_utc)` depends on it. Changing that table under a DAG run in progress
would fail the load. With a second table, a deploy only adds a table, and nothing reads or writes
`flood_depth_raster` after it. Since 2026-09-24, `create_flood_depth_raster_tables.py` no longer
creates `flood_depth_raster`. A database set up before then still holds the table and the rows
loaded before the switch, until the deploy runbook in [[raster-first-flood-pipeline]] runs
`DROP TABLE IF EXISTS flood_depth_raster;`.

## Retention

`publish_run`'s `prune_bucket_runs` keeps the newest `FLOOD_EXTENT_KEEP_RUNS` runs (default 3) in
the bucket, always preserving the run currently being published, and deletes every object under
older `runs/<run>/` prefixes in batches of 1,000 keys (the `DeleteObjects` API's per-call cap).
Local scratch space (`FLOOD_EXTENT_WORK_DIR`, plus the depth directory itself) is separately swept
by `cleanup_old_files`, which deletes any top-level child older than
`FLOOD_EXTENT_CLEANUP_MAX_AGE_HOURS` (default 24), using each child's newest file's mtime as its
age so a folder still being written is never mistaken for a stale one.

`raster_load.load_run` prunes `flood_depth_raster_tile` the same way after it loads a run. It keeps
the newest `keep_runs` runs by `run_ts` and deletes every tile of older runs. A caller that passes
no `keep_runs` gets `FLOOD_RASTER_KEEP_RUNS` (default 3), which is what `flood_mapping_full` does.
The manual two-event test DAG passes 1,000, so a test run never prunes production tiles. The load
never deletes the run it just loaded, even when an older run is loaded again later. A value below
1 fails the load.

## How the frontend picks a timestep

**Branch `fifteen-minute-cycle` (not deployed) changes the rest of this section.** `publish_run` builds
tiles and polygons for the first `tile_steps` steps of a run only (`FLOOD_EXTENT_TILE_STEPS`, default 2).
After a step's tiles and polygon rows are written, it records the step in `flood_extent_step`
(`run_ts`, `valid_time_utc`, `is_empty`, `published_at`), which is the published flag. `GET /flood/timesteps`
reads that table and returns, for each time, the newest run that published it, so entries can carry
different runs and dry steps stay in the list. `FloodStore.ts` selects the latest step at or before now
(`findNowTimestepIndex`) and re-picks on every refetch. Retention rises to 8 runs. Runs published before
the table existed are backfilled only when the table is empty, from the newest 3 runs. The raster load
still covers every step, and `POST /flood/forecast` reads it for the route depth chart.
The text below describes the code on the deployed branch.

`GET /flood/timesteps` lists the timesteps of one run only, the newest `run_ts` in
`flood_extent_polygon`. A timestep with no flooding has no polygon row, so it is not in the list.
On load, `floodmap/graphhopper-maps/src/floodmap/FloodStore.ts` selects the timestep closest to
now (`reanchorTimestepIndex`). The store starts with `mapMode: 'flood'` and `userChoseMapMode: true`,
a demo default, so the page opens in flood mode whatever the timestamps say. `defaultMapMode`, which
would open in flood mode only when the newest timestep is within `FRESH_DATA_WINDOW_MS` (45 minutes)
of now, exists but is not used at load while that demo default stays. `useFloodBootstrap`
re-fetches the timestep list well inside that window so the map picks up a new run promptly.

## Open items

- `artifacts/docs/claude-plan/flood-extent-polygon-tiles-airflow-minio.md` is the plan this
  pipeline was built from; the parts already shipped (per-timestep tiles, MinIO storage, the
  45-minute freshness window, the timezone conversion) are described above as built. Check that
  plan file's own status before assuming anything past what this page states is still open.
- GRASS GIS still runs the raster-to-polygon step inside `flood_extent.py`; no GRASS-free rewrite
  is planned.
