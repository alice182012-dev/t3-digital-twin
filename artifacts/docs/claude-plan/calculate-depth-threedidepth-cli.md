# calculate_depth CLI pattern + production polygon pipeline

## Context

Two things need to happen in sequence on `flood-tile-t6t7`:

1. `scripts/calculate_depth.py` already wraps `threedidepth.calculate_waterdepth()`
   and already emits one single-band GeoTIFF per timestep — the "combines
   timesteps into bands of one raster" problem doesn't apply to this wrapper.
   `compose.yml` line 30 (`MAX_WORKERS: ${MAX_WORKERS:-1}`) only looks
   under-provisioned in isolation: `.env` already sets `MAX_WORKERS=8` and
   `AIRFLOW_WORKER_CONCURRENCY=2` (line 47), so the fallback of `1` never
   actually applies today. Those two numbers combine, though — Celery lets 2
   tasks run at once per worker container, and each task's own
   `run_calculate_depth` call spawns up to 8 processes, so two overlapping
   heavy tasks (e.g. `calculate_depth` running for both events in
   `flood_forecast_state_test_dag.py`, or `calculate_depth` overlapping with
   an unrelated task) can ask for up to 16 concurrent processes. This needs
   checking against actual host core count, not blindly bumped further. The
   user separately wants the per-timestep calculation restructured to call
   `threedidepth`'s own packaged CLI
   (`threedidepth gridadmin results_3di dem waterdepth -s STEP`, see
   `commands.py` in the installed package) via subprocess, rather than
   calling `calculate_waterdepth()` in-process — matching how every other
   step in this pipeline (GRASS, `gdal_polygonize.py`, `ogr2ogr`) already
   shells out to a CLI tool instead of importing a Python API.
2. `compose.override.yml` is unrelated to this work — it's a local-only
   stopgap that mounts a substitute OSM extract for the `graphhopper` service
   because the real `hanoi-model-area.osm.pbf` isn't on this machine yet. It
   touches no flood-depth or tile code. Leave it as-is; nothing in this plan
   changes it.
3. There's already a throwaway pattern for testing `calculate_depth` without
   a full 3Di trigger/download cycle: `dags/test_dag.py`'s
   `task_calculate_depth` hardcodes `nc_path =
   "/opt/airflow/data/test/results_3di.nc"` and reuses the existing
   `data/inputs/gridadmin.h5` / `data/inputs/dem.tif` fixtures already on
   disk. The user wants a dedicated manual DAG built the same way, so the new
   CLI-subprocess logic can be iterated on and validated on its own before
   Part B (the polygon/DB/cleanup work) starts.
4. `scripts/flood_extent/flood_extent.py` (GRASS + GDAL polygon pipeline) has
   a prior plan at
   `artifacts/docs/claude-plan/flood-extent-polygon-tiles-airflow-minio.md`
   which got tiles working end-to-end on this laptop (measured ~110s/timestep,
   187 tiles for a real run) but stopped short of Airflow wiring, MinIO, and
   the nearest-timestep manifest. That plan is still the right shape for
   "closest timestep to NOW" serving — this plan extends it, it doesn't
   replace it. New requirements layered on top: persist polygons to
   PostGIS (currently zero DB writes happen — confirmed by full-file read of
   `flood_extent.py`), delete raw `depth_*.tif` and intermediate output after
   24 hours (currently nothing does — `tif_dir_to_clean=None` in
   `flood_mapping_dag.py` line 248 means depth tifs accumulate forever), and
   color the polygon bands using the reference QML style
   (`test/waterdepth_steps/waterdepth_steps/depth_20251006_000000.qml`) so the
   legend matches. The old raster-tile viz (`tiles.py`, `/tiles/` endpoint,
   rio-tiler) is already fully deleted, in commit `2d600c8` — nothing to do
   there beyond removing one stale comment in `depthScale.ts`.

`calculate_depth.py` is flagged fragile in memory — changes go on a branch and
get validated against `dags/flood_forecast_state_test_dag.py` before touching
the production DAG.

## Decisions made in brainstorming

- Tile serving stays **static files + nginx**, not a dynamic tile server. The
  "closest timestep to NOW" requirement (e.g. now=14:17, serve the 14:19
  tiles) is a manifest-and-pick problem, not a query problem — it's already
  designed in the existing plan's `latest.json` + `pickExtentStep` step. A
  dynamic pg_tileserv/martin service would add a new container and a new
  failure mode for no benefit here, since nothing needs ad hoc spatial
  queries against the polygons.
- PostGIS becomes an **audit table**, not the tile source: `flood_extent_polygon`
  in `storage-postgres` (same instance as `flood_road_values`), written
  alongside the tile publish step, following the existing
  `create_geojson_tables.py` pattern (idempotent DDL, GIST index).
- QML colors: sample the QML's interpolated blue ramp at the existing
  `BAND_TABLE` cm thresholds to get one fixed hex color per band, rather than
  switching to a true continuous per-pixel raster style. Keeps the current
  discrete-polygon-band architecture in `flood_extent.py`/`depthScale.ts`,
  just makes the colors match the reference.

## Part A — calculate_depth via the threedidepth CLI

Files: `scripts/calculate_depth.py`, new `dags/calculate_depth_manual_test_dag.py`.
No `compose.yml`/`.env` edits are expected — `MAX_WORKERS=8` and
`AIRFLOW_WORKER_CONCURRENCY=2` are already set; this work only checks they're
sane, it doesn't change them unless the check finds a problem.

This part must be fully validated before Part B starts, per the user's
explicit sequencing.

1. **New manual test DAG**, `dags/calculate_depth_manual_test_dag.py`, modeled
   on `dags/test_dag.py`'s `task_run_simulation`/`task_download_result` and
   `flood_forecast_state_test_dag.py`'s single-event trigger pattern: trigger
   one real 3Di simulation (fixed synthetic rain, cold start), download it,
   then run `calculate_depth.run_calculate_depth` against the result (grid
   and DEM stay the shared local fixtures, `data/inputs/gridadmin.h5` and
   `data/inputs/dem.tif`). State file, result dir, and output dir are all
   isolated (`state/flood_state_cli_test.json`, `data/results_cli_test/`,
   `data/output_depths_cli_test/`) so a run here never collides with
   production state/output or with `flood_forecast_state_test_dag.py`'s
   hotstart test tree. This exists to validate the CLI-subprocess rewrite
   (step 3 below) end to end against a real simulation, without the
   two-event hotstart chain `flood_forecast_state_test_dag.py` adds.
2. **Check the worker-count interaction**, not the values themselves: confirm
   host/container CPU count against `AIRFLOW_WORKER_CONCURRENCY=2` ×
   `MAX_WORKERS=8` (up to 16 concurrent processes if two heavy tasks overlap).
   Only touch `compose.yml`/`.env` if this check finds actual oversubscription
   on the target host.
3. **Replace the in-process `calculate_waterdepth()` call** in
   `process_single_step` with a `subprocess.run([...])` call to the installed
   `threedidepth` console script: `threedidepth <grid_path> <nc_path>
   <dem_path> <temp_path> -s <step_index>` (single step per invocation, so
   output stays single-band — never pass multiple `-s` values, which is what
   produces the multi-band raster the user wants to avoid). Keep everything
   downstream of the raw output unchanged: `validate_depth_raster`,
   `get_time_from_tif_and_clean`, the atomic temp-dir-then-rename pattern, and
   the `billiard.Pool`-based parallelism across timesteps (only the body of
   each worker task changes from a function call to a subprocess call).
   Surface subprocess stderr/non-zero exit into the existing `"❌ ..."`
   failure-string convention so `run_calculate_depth`'s failure aggregation
   still works unmodified.
4. **Validate on a branch** using the new manual test DAG first (fast
   iteration against local fixtures), then `dags/flood_forecast_state_test_dag.py`
   (never edit `calculate_depth.py` against the production DAG directly, per
   the fragility note in memory). Confirm: output filenames/timestamps
   unchanged, same single-band shape, and wall-clock time with the
   subprocess-based CLI calls is not worse than the current in-process calls.

## Part B design update (2026-09-22)

Before implementing, confirmed with the user that production runs the
Airflow worker and the flood-routing-frontend on **separate hosts** — so the
old plan's local-bind-mount tile serving (still what's actually deployed
today; the old MinIO plan's steps 1-4 were never built despite the old
plan's status section implying otherwise) cannot work in production and
MinIO is required, not optional.

Re-reading the frontend with that constraint in mind found a simplification
of the old plan's steps 1-4: `FloodStore.ts` already tracks `{run,
valid_time}` timesteps from Postgres (`flood_road_values`, populated by the
same `run_ts` the tile pipeline uses) with `findNearestTimestepIndex` and a
45-minute `FRESH_DATA_WINDOW_MS` cutoff, both already used to drive
`FloodExtentLayer.tsx`'s selected timestep prop
(`floodmap/graphhopper-maps/src/floodmap/FloodExtentLayer.tsx:29`,
`floodExtentTiles.ts`). Building a second, parallel `latest.json`
manifest + `pickExtentStep` system, as the old plan speced, would duplicate
that working mechanism. Instead:

- Tiles move from the local bind mount to a new private MinIO bucket
  (`FLOOD_EXTENT_BUCKET`), reusing `scripts/mapping/upload_minio.py`'s
  `get_s3_client()` pattern and the already-wired `MINIO_ENDPOINT`/
  `MINIO_ACCESS_KEY`/`MINIO_SECRET_KEY` env vars in `compose.yml`'s
  `x-airflow-common-env` (`compose.yml:22-28`).
- `nginx.conf`'s `/flood-extent/` location changes from `try_files` against
  the bind mount to a `proxy_pass` against MinIO, mirroring the existing
  `/api/gh/` `resolver`/`set $backend_host` pattern (`nginx.conf:21-33`).
  The URL path stays `/flood-extent/<run>/<timestep>/{z}/{x}/{y}.pbf`, so
  `floodExtentTilesUrl()` and `FloodExtentLayer.tsx` need no changes.
- No new manifest file. The only real frontend gap is that nothing
  currently re-fetches timesteps or re-evaluates the NOW-relative pick on a
  timer (`useFloodBootstrap` in `useFloodState.ts:29-40` calls
  `loadFloodTimesteps()` once, on mount, confirmed by grep — no
  `setInterval` anywhere in the frontend). Adding periodic refresh there
  fixes staleness for road overlays and the flood-extent layer at once.

## Part B — production polygon pipeline

Files: `scripts/flood_extent/flood_extent.py`, `scripts/flood_extent/publish.py`
(new, per the existing plan doc), `scripts/database/create_geojson_tables.py`
(pattern to follow, not edit directly — new file
`scripts/database/create_flood_extent_tables.py` or extend the existing
schema module), `dags/flood_mapping_dag.py`, `dags/flood_forecast_state_test_dag.py`,
`floodmap/graphhopper-maps/src/floodmap/depthScale.ts`,
`floodmap/graphhopper-maps/src/floodmap/extentTimeline.ts` (new, per existing
plan doc).

1. **Pick up the existing plan's open steps 1–4 as-is**: `publish.py` module
   (`publish_run`, `valid_time_utc`, manifest write-last ordering),
   `extentTimeline.ts` (`pickExtentStep` nearest-timestep-to-NOW logic, the
   45-minute freshness cutoff), and the frontend polling/re-pick loop in
   `FloodExtentLayer.tsx`. This is exactly the "now=14:17, serve 14:19"
   mechanism the user asked about — no new design needed here, just finish
   what's already speced.
2. **Add the PostGIS audit table**, written by `publish_run` right after a
   successful tile publish for a run (not before — mirrors the "write
   `latest.json` only after every step succeeds" rule already in the plan).
   Schema: `flood_extent_polygon(id, run_ts, valid_time_utc, dn_code, area_m2,
   geom geometry(Geometry,4326), created_at)`, GIST index on `geom`, following
   `create_geojson_tables.py`'s idempotent `CREATE TABLE IF NOT EXISTS` +
   `postgis` extension pattern. One row per dissolved band polygon per
   timestep (source: `flood_extent.py`'s `cleaned.gpkg`, before tiling).
3. **QML-derived band colors**: write a small script/notebook step to sample
   the QML's `INTERPOLATED` blue ramp (`test/waterdepth_steps/.../*.qml`,
   9 breakpoints between `classificationMin`/`classificationMax`) at the
   `BAND_TABLE` cm thresholds in `flood_extent.py`, producing one fixed hex
   color per band. Apply that palette to `depthScale.ts`'s
   `DISPLAY_DEPTH_BANDS` (frontend legend/fill colors) so it matches the
   reference style. Remove the stale comment there referencing the deleted
   `backend/tiles.py`.
4. **24-hour temp file cleanup**: no existing pattern for age-based deletion
   (`prune_runs` is count-based). Add a small Airflow task (or extend
   `publish_run`) that walks `output_depths/` and the polygon work dirs and
   deletes anything with `mtime` older than 24 hours, run after tile publish
   succeeds. This closes the gap where raw `depth_*.tif` dirs currently
   accumulate forever (`tif_dir_to_clean=None` in `flood_mapping_dag.py`
   line 248).
5. **Wire into both DAGs**: production `flood_mapping_dag.py` gets the new
   `publish_run`/DB-write/cleanup task chained after `9_build_flood_tiles`
   (or replacing it, if `publish_run` subsumes `build_run_tiles`). For manual
   end-to-end testing, extend `flood_forecast_state_test_dag.py` with the same
   chain after its `calculate_depth` tasks, since the user will test the full
   pipeline through that DAG rather than waiting on real rain in production.
6. **Docker**: no new services — GRASS/GDAL are already in the `airflow-worker`
   image (`Dockerfile`, `grass-core` in the final apt layer), tiles keep being
   served by the existing nginx bind-mount, and the new DB writes go to the
   already-running `storage-postgres` container. Confirm `compose.yml`'s
   `flood-routing-frontend` mount and `FLOOD_EXTENT_TILES_DIR` still line up
   with `publish_run`'s output layout.

## Verification

- Part A: run `flood_forecast_state_test_dag.py` on a branch, compare
  `depth_*.tif` output (filenames, single-band shape, pixel values) before
  and after the CLI-subprocess change; confirm wall-clock time improves with
  `MAX_WORKERS=8`.
- Part B: run the same test DAG end-to-end through the new tile-publish +
  DB-write + cleanup tasks. Check: tiles appear at the expected MinIO key and
  render in the browser (gstack `/browse`) with QML-matched colors, rows land
  in `flood_extent_polygon`, `FloodStore`'s existing nearest-timestep-to-NOW
  logic (`findNearestTimestepIndex`, `FRESH_DATA_WINDOW_MS`) picks correctly
  once periodic refresh is live (see the Part B design update above; there is
  no `latest.json` manifest in the built version), and files older than 24
  hours are actually removed after a run.
- Python: `python3 -m unittest discover -s scripts/flood_extent -p "test_*.py"`.
- Frontend: `tsc --noEmit` and `jest` for `floodmap/graphhopper-maps` changes.

## Progress log

- 2026-09-22: Plan approved. Branch `calculate-depth-cli-subprocess` created
  off `flood-tile-t6t7` for Part A. Starting with the manual test DAG.
- 2026-09-22: Part A steps 1–4 done and verified.
  - Step 1 (manual test DAG): `dags/calculate_depth_manual_test_dag.py` added.
    First version called `calculate_depth.run_calculate_depth` directly
    against fixed local fixtures (no simulation trigger). Revised after
    feedback that the manual test should exercise the full chain starting
    from the simulation trigger, not just `calculate_depth`: it now triggers
    one real 3Di simulation (fixed synthetic rain, cold start) via
    `create_simulation.run_forecast_process`, downloads it, then runs
    `calculate_depth.run_calculate_depth` on the result — isolated state
    file/result dir/output dir (`state/flood_state_cli_test.json`,
    `data/results_cli_test/`, `data/output_depths_cli_test/`). Reviewed via
    `pstack:poteto-mode` against its two model DAGs (`test_dag.py`,
    `flood_forecast_state_test_dag.py`): dropped a dead-code
    delete-state-file-then-cold-start block copied from the hotstart DAG —
    `use_saved_state=False` already skips reading `state_file_path`
    regardless of whether the file exists, so the deletion could never
    change behavior.
  - Step 2 (worker-count check): host/`airflow-worker` container both report
    12 cores, no `cpuset`/`NanoCpus` limit set on the container. Worst case
    (`AIRFLOW_WORKER_CONCURRENCY=2` × `MAX_WORKERS=8` = 16) mildly
    oversubscribes 12 cores (~33%), but not enough to call "actual
    oversubscription" given the workload isn't purely CPU-bound (raster I/O
    per subprocess). Left `compose.yml`/`.env` untouched, per the plan's
    "only touch if the check finds a problem" rule.
  - Step 3 (subprocess rewrite): done in `scripts/calculate_depth.py`
    (`process_single_step` now shells out to the `threedidepth` console
    script with a single `-s` value; non-zero exit surfaces into the
    existing `"❌ ..."` failure-string convention).
  - Step 4 (validation): ran `calculate_depth_manual_test` via
    `airflow dags test` in `airflow_new-airflow-worker-1` against the local
    fixtures. Output filenames and single-band shape matched. A first
    pixel-diff against `data/output_depths/depth_20260704_170000_180000/`
    (produced 2026-09-04 by `test_dag.py`'s in-process call) showed large
    differences (max abs diff ~7.76) — traced to that baseline predating a
    2026-09-12 update to `data/inputs/gridadmin.h5`, not a subprocess-rewrite
    bug. Regenerated a same-fixtures baseline by running the pre-branch
    `calculate_depth.py` (`git show HEAD:scripts/calculate_depth.py`)
    in-process against the identical current fixtures: output was
    pixel-identical (`np.array_equal`) to the new CLI-subprocess output for
    both timesteps. Scratch output dirs removed after comparison.
  - The step 4 validation above (pixel-identical output) ran against the
    first, fixture-only version of the manual test DAG, before it was
    revised to trigger a real simulation.
- 2026-09-22: User confirmed Part A is done (ran the revised manual test DAG
  and `flood_forecast_state_test_dag.py` themselves). Moving to Part B.
- 2026-09-22: Part B built and verified. Confirmed with the user that
  production runs the worker and frontend on separate hosts, which settled
  the design fork recorded above (MinIO required; local-manifest system
  dropped in favor of `FloodStore`'s existing Postgres-driven nearest-
  timestep logic). QML color sampling: literal meter-value interpolation
  would have compressed six of seven bands into near-identical pale blues
  (computed and shown to the user), so used rank-order mapping onto the
  ramp's 9 ColorBrewer-Blues stops instead, per the user's choice.
  - `scripts/flood_extent/flood_extent.py`: `Pipeline.check()` now also
    reprojects each band's dissolved polygon to EPSG:4326 and returns it via
    a new `FloodExtentResult.polygons_4326` field. Verified against a real
    depth raster (Hanoi-area lon/lat envelopes, all geometries valid).
    Removed `build_run_tiles`/`prune_runs` (local-disk multi-timestep
    publish) since `publish.py` replaced their only caller
    (`flood_mapping_dag.py`'s task 9) and they had zero remaining callers.
  - New `scripts/database/create_flood_extent_tables.py`: `flood_extent_polygon`
    audit table, UNIQUE(run_ts, valid_time_utc, dn_code) for idempotent
    upserts on task retry, GIST index. Verified live against
    `storage-postgres`.
  - New `scripts/flood_extent/publish.py`: `valid_time_utc` (Vietnam-time
    filename to UTC, used for the DB column only — S3/tile keys stay in the
    same local-time key format `FloodStore`/`floodExtentTilesUrl()` already
    use, so the frontend needed no changes), `publish_run` (parallel tile
    build + MinIO upload via a thread pool, sequential DB upserts after
    since a psycopg2 connection isn't thread-safe, bucket pruning and 24h
    local cleanup gated on zero timestep failures), `cleanup_old_files`.
    `test_publish.py` added (7 unit tests, passing). Verified end to end
    against a real depth-raster fixture, the real `storage-postgres`, and a
    scratch MinIO bucket: correct keys, correct upserted rows, correct
    areas/geometry types.
  - `compose.yml`/`minio-init`: new `flood-extent` bucket with anonymous
    download (the only bucket that's public; the MinIO API port itself
    stays bound to 127.0.0.1). `FLOOD_EXTENT_BUCKET` env var added.
    Frontend's old local bind mount removed. Verified: `docker compose
    config` valid, `minio-init` re-run created the bucket live.
  - `floodmap/graphhopper-maps/nginx.conf`: `/flood-extent/` now proxies to
    `minio:9000` (mirroring the existing `/api/gh/` pattern) instead of
    `try_files` against a bind mount. Verified live: rebuilt and restarted
    `flood-routing-frontend`, fetched a real published tile through it (200,
    correct content-type) and a missing one (404, not the SPA fallback).
  - `dags/flood_mapping_dag.py`: task 9 now calls `publish.publish_run`
    instead of `flood_extent.build_run_tiles`; `0b_ensure_schema` also
    ensures the new table. Verified by invoking the real task function
    through a mock `TaskInstance` against real fixture data (not just
    `publish.py` in isolation) — correct run_ts derivation, correct bucket,
    tiles served through nginx afterward, rows landed in Postgres.
  - `dags/flood_forecast_state_test_dag.py`: added `3b_build_tiles_event1`/
    `6b_build_tiles_event2` after each event's depth calc, isolated to the
    test tree, `keep_runs=1000` so test runs (whose `run_ts` values sort
    among real production runs in the same bucket) can never prune a
    still-good production run. Not yet run as a real DAG execution (would
    cost two more 3Di simulations); left for the user, consistent with
    Part A's simulation-triggering DAGs.
  - `floodmap/graphhopper-maps/src/floodmap/depthScale.ts`: QML-derived
    colors applied (rank-order mapping, see above), stale `backend/tiles.py`
    comment removed.
  - `floodmap/graphhopper-maps/src/floodmap/FloodStore.ts` /
    `useFloodState.ts`: added `TIMESTEP_REFRESH_INTERVAL_MS` (5 min) periodic
    refetch in `useFloodBootstrap`, closing the gap where `loadFloodTimesteps()`
    only ever ran once, on mount. `reanchorTimestepIndex`'s existing
    "follow the current selection if it still exists" behavior is
    intentional (documented) and left alone; periodic refresh's job is
    surfacing new production runs without a page reload, not overriding
    that.
  - Verified: `tsc --noEmit` and the full Jest suite (177 tests, 17 suites)
    pass in the `gh-maps-dev` container.
  - All smoke-test tiles, DB rows, and scratch work dirs removed after each
    verification step; nothing test-related left in the real bucket, table,
    or filesystem.
  - Not done: no real Airflow-scheduled run of either DAG (both would
    trigger real, billed 3Di simulations); the worker/scheduler/dag-processor
    containers haven't been recreated to pick up `FLOOD_EXTENT_BUCKET` in
    their baked-in environment (every new env var has a matching code
    default, so this isn't blocking, just means a restart hasn't been
    exercised yet).
