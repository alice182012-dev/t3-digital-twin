---
date: 2026-09-18
type: plan
branch: flood-tile-t6t7
status: done
tags: [flood-tile, airflow, minio]
related: ["[[2026-09-18]]", "[[raster-first-flood-pipeline]]"]
---

# Flood-extent polygon tiles: Airflow, MinIO, and view-time serving

## Context

The map now draws flood depth as polygon vector tiles (commits `55f0159` and `99dd553` on `flood-tile-t6t7`). Today the tiles come from one hand-built folder (`data/flood-extent/mvt`) that is bind-mounted into the frontend container.

Production needs the tiles built by Airflow for every forecast timestep, stored in MinIO, and served to the map. This plan covers the whole path, and the first milestone is a working end-to-end test on this laptop with the local MinIO before anything runs on the server.

## Decisions already made

- Build tiles for every timestep of a run. The browser picks the step closest to NOW when the page loads and again as the clock moves.
- If the closest step is more than 45 minutes from NOW, show no flood layer. The 45 minutes matches `FRESH_DATA_WINDOW_MS` in `FloodStore.ts`. Confirm this value.
- The tile build is a parallel branch in the DAG, after `3_calculate_depth`. It does not block the road-mapping chain.
- The road-mapping chain (extract GeoJSON, merge, map roads, upload, Postgres) stays. Routing keeps reading flood data from PostGIS. Unifying routing with the raster is a separate task.
- One depth GeoTIFF per timestep, one band. `scripts/flood_extent/flood_extent.py` already handles that shape, including dry timesteps.
- GRASS GIS will be installed on the server. No GRASS-free rewrite of the closing step.

## Facts that shape the design

- Depth filenames are in Vietnam time (UTC+7). `scripts/calculate_depth.py` converts the 3Di UTC time to local time before it writes `depth_YYYYMMDD_HHMMSS.tif`. The publish step must convert the filename time back to UTC, or the closest step will be off by 7 hours.
- The DAG (`dags/flood_mapping_dag.py`) runs continuously with `max_active_runs=1`. A run takes about 24 minutes, and the road-mapping steps are about 20 of them, so a tile branch of about 2 minutes per step fits inside that time.
- The Airflow scripts use `boto3` against MinIO (`scripts/mapping/upload_minio.py`). Reuse its `get_s3_client` and the `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` variables. `boto3` is not installed in the host Python, so local tests run in a container or a virtual environment.
- The Airflow image (`Dockerfile`) has `gdal-bin` and `libgdal-dev` but no GRASS.
- Local MinIO is already running (`t3-digital-twin-minio-1`, API on `127.0.0.1:9000`). `minio-init` in `compose.yml` creates the buckets.
- Measured on this laptop: one timestep takes about 110 seconds (reclassify 2 s, close bands 20 s, polygonize 2 s, dissolve 63 s, clean 1 s, tiles 21 s) and writes about 190 tiles, 24 MB. Each run leaves about 350 MB of intermediate files.

## Data shape

Bucket `flood-extent` (name in env `FLOOD_EXTENT_BUCKET`):

- `runs/<runTs>/<validUtc>/{z}/{x}/{y}.pbf` for the tiles of one step. `validUtc` is compact UTC, for example `20251006T170000Z`.
- `latest.json`, written last, is the commit point:

```json
{ "run": "20251007_000000", "timesteps": ["2025-10-06T17:00:00Z", "2025-10-06T17:30:00Z"] }
```

The manifest lists every step of the run, including dry steps that have no tiles. A dry step then shows an empty map, which is correct. A tile that does not exist returns 404, and the map treats that as empty.

Publish order gives safe updates. Upload all tiles first, write `latest.json` last, then prune old runs. If any step fails, do not write `latest.json`. The map keeps the previous run.

## Steps

### 0. Housekeeping when plan mode ends

1. Copy this plan to `artifacts/docs/claude-plan/flood-extent-polygon-tiles-airflow-minio.md`.
2. Add a rule to the project `.claude/CLAUDE.md`: write the plan of any multi-step task to `artifacts/docs/claude-plan/`, in a file whose name says what is being built, before starting the work.

### 1. Publish module

New `scripts/flood_extent/publish.py`, with unit tests in `scripts/flood_extent/test_publish.py`.

- `valid_time_utc(filename)` parses `depth_YYYYMMDD_HHMMSS.tif` as UTC+7 and returns UTC.
- `publish_run(depth_dir, run_ts, work_dir, s3, bucket, workers)` does the following:
  - build each step with `Pipeline` from `flood_extent.py`, in a thread pool (default 2 workers, to be set after step 6)
  - upload each step's `mvt/` files with `boto3` and content type `application/x-protobuf`
  - delete the step's work folder after upload
  - write `latest.json` only after every step succeeds
  - prune runs older than the newest two
- Fail loudly on any step error. No partial manifest.

Tests: the UTC+7 conversion, key layout, manifest contents, and that the manifest is not written when one step fails.

### 2. MinIO bucket and nginx

- `compose.yml`, `minio-init`: create `flood-extent` and set anonymous download on it (`mc anonymous set download`). The MinIO API port stays bound to `127.0.0.1`, so the bucket is public only through nginx.
- `floodmap/graphhopper-maps/nginx.conf`: replace `location /flood-extent/` with a proxy to `http://minio:9000/flood-extent/`. Use the `resolver` and `set $var` pattern already in the file. Return 404 for missing objects. Set `Cache-Control: no-cache` on `latest.json` and `public, max-age=3600` on tiles.
- `compose.yml`, `flood-routing-frontend`: remove the bind mount of `data/flood-extent/mvt`.

### 3. Frontend selection at view time

- New `src/floodmap/extentTimeline.ts` with a pure `pickExtentStep(timesteps, now, maxGapMs)`. It returns the closest step, or `null` when the closest is farther than `maxGapMs` or the list is empty. Reuse the nearest-step logic in `findNearestTimestepIndex` (`FloodStore.ts`) if it fits the tie rule (later step wins).
- `src/floodmap/FloodExtentLayer.tsx`:
  - fetch `latest.json` on mount and every 5 minutes
  - re-pick the step every minute, and set the source URL to `/flood-extent/runs/<run>/<validUtc>/{z}/{x}/{y}.pbf`
  - hide the layer when `pickExtentStep` returns `null`
- Tests in `test/floodmap/extentTimeline.test.ts`: closest step, tie, all in the past, all in the future, the 45 minute cutoff, empty list.

### 4. Local end-to-end test

1. Start the stack with the new MinIO bucket and nginx proxy.
2. Make copies of the five test rasters in `test/waterdepth/depth_20251007_000000_20251007_020000/`, renamed so their Vietnam-time names fall around the current time (now minus 30 minutes up to now plus 90 minutes).
3. Run `publish.py` against them with the local MinIO credentials from `.env` (`MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`).
4. Check in the browser (gstack `/browse`) that the layer shows and the request URL contains the closest step.
5. Check "serve nothing": publish a manifest whose steps are all more than 45 minutes old and confirm the layer is hidden with no console errors.
6. Check a dry step: publish a synthetic all-nodata raster and confirm the tiles 404 quietly and the map shows no polygons.

### 5. Airflow integration

- `dags/flood_mapping_dag.py`: add task `3c_build_flood_extent` that calls `publish_run` on the depth directory returned by `3_calculate_depth`. Wire `t3 >> t3c` so it runs beside `t4 ... t8`.
- `Dockerfile`: install GRASS (Debian package `grass-core`, provides the `grass` command). Check the installed version is 8.x.
- `compose.yml`: pass `FLOOD_EXTENT_BUCKET` and the publish settings to the Airflow services.
- Local check: run the task callable on the test rasters inside the rebuilt Airflow image. A full DAG run needs the 3Di API and starts a real simulation, so it is out of local scope. Parse the DAG file to confirm it loads.

### 6. Measure before the server

- Peak memory of one GRASS run (`/usr/bin/time -l`), then set the default worker count from the server's RAM.
- Wall time of a full 8-step publish with 1 and 2 workers, compared with the 20-minute road-mapping chain.

### 7. Server rollout checklist

- Install GRASS on the server or rebuild the Airflow image.
- Create the bucket and policy in the server MinIO.
- Deploy nginx and frontend.
- Watch the first two runs: manifest updates, old run pruned, no 404 storm from the map.

## Risks and open questions

- Memory: GRASS on a 56 million cell raster is untested for peak RAM. Step 6 decides the worker count.
- The 45 minute cutoff and 30 minute step spacing mean a run that finishes late can leave a gap in which no step is close enough. Watch this in the first server runs.
- A public-read bucket exposes only derived tiles. Confirm that is acceptable for production.
- Frontend manifest polling: 5 minutes is a guess. Tune it after seeing the real run cadence.
- Routing and the map can show different floods until routing reads the same raster. Tracked as a separate task.

## Verification

- Python: `python3 -m unittest discover -s scripts/flood_extent -p "test_*.py"`.
- Frontend: run `tsc --noEmit` and `jest` in a Node container against `floodmap/graphhopper-maps` (host `npm install` is blocked).
- End to end: step 4 above, with screenshots.
- Performance: the numbers from step 6 go into the plan file when measured.

## Status: done, MinIO path shipped

The plan's own fork in its Open list (continue toward MinIO, or keep the
volume-based layout) resolved toward MinIO. Confirmed against the current
code, not just recollection: `scripts/flood_extent/publish.py` exists and is
what `dags/flood_mapping_dag.py`'s task 9 calls
(`publish.publish_run(..., FLOOD_EXTENT_BUCKET, ...)`, uploading to
`s3://flood-extent/runs/<run_ts>/...`), and `compose.yml` no longer bind-mounts
`data/flood-extent/mvt` into `flood-routing-frontend`; `/flood-extent/` is
proxied to the `minio` service's `flood-extent` bucket instead (see
`compose.yml` lines 36-38, 93, 105-110, 384-389).

Implemented, superseding the "first milestone" section below:

- `scripts/flood_extent/publish.py`: builds each timestep, uploads its tiles
  to MinIO, and writes the run's manifest.
- `dags/flood_mapping_dag.py` task 9 (`build_flood_tiles`) calls `publish_run`
  after `5_merge_geojson`, publishing per-run, per-timestep tiles to
  `s3://flood-extent/runs/<run_ts>/...` and pruning old runs
  (`FLOOD_EXTENT_KEEP_RUNS`).
- `compose.yml`: `minio-init` creates the `flood-extent` bucket with anonymous
  download; the frontend's `/flood-extent/` path is proxied to MinIO, not
  bind-mounted.

Not re-verified in this pass: view-time manifest selection against
`FRESH_DATA_WINDOW_MS`, the 45-minute-cutoff and dry-step UI behavior, and
worker peak-memory/wall-time figures. These aren't blocking anything currently
in flight; revisit only if a flood-extent-tile bug surfaces.

<details>
<summary>Superseded: "first milestone built without MinIO" (2026-09-21 snapshot)</summary>

Built on `flood-tile-t6t7`, not committed at the time. This milestone chose
display-only scope and precomputed tiles, and skipped MinIO, the manifest, and
view-time selection by the clock.

- `scripts/flood_extent/flood_extent.py` is an importable engine.
  `build_flood_extent` builds one timestep, and `build_run_tiles` builds a run.
  Every intermediate file lives in a temporary folder that is always deleted.
  The tile folder is swapped in only when it is complete.
- Tiles went to `data/flood-extent/<run>/<timestep>/{z}/{x}/{y}.pbf`, bind-mounted
  into `flood-routing-frontend` — since superseded by the MinIO path above.
- `FloodExtentLayer.tsx` follows the timestep selected in `FloodStore` and
  re-points one layer as the timeline moves.
- `Dockerfile` installs `grass-core` in the last apt block.

Checked at the time: the engine ran on a real raster in a container with GRASS
8.2.1 (187 tiles, no files left in `/tmp`), including dry, one-cell, and
corrupt inputs. `tsc` and the floodmap Jest suites passed.

</details>

## Note, 2026-09-24: the road-mapping chain left the DAG

Two statements in this plan no longer hold. The "Decisions already made" section says the
road-mapping chain stays, and the Status section says task 9 runs after `5_merge_geojson`. Both were
true when written. The plan [[raster-first-flood-pipeline]] removed tasks `4_extract_geojson_full`
to `8_upload_postgres` from `dags/flood_mapping_dag.py`. Task `9_build_flood_tiles` runs after
`3_calculate_depth` and takes `run_ts` from `flood_extent.run_ts_for_depth_dir`, the `stamp_key` of
the earliest `depth_*.tif`. The tile path this plan built is otherwise unchanged.

No DAG task writes `flood_road_values` until Story 3 of [[raster-first-pipeline-stories]] lands, and
routing still reads that table. Do not deploy the DAG before then.
