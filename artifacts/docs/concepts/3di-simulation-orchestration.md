---
date: 2026-09-22
type: concept
status: active
tags: [3di, airflow, simulation]
related: ["[[SW Architecture]]", "[[calculate-depth-threedidepth-cli]]", "[[minio-flood-extent-pipeline]]", "[[raster-first-flood-pipeline]]"]
last_updated: 2026-09-24
---

# 3Di simulation orchestration

`dags/flood_mapping_dag.py` runs one continuous cycle: check the rain forecast, decide whether to
run a 3Di simulation, run it, download the result, turn it into depth rasters, and hand those to
the flood-extent tile task and the depth raster load. This page covers the first three steps,
through the depth raster. See [[minio-flood-extent-pipeline]] for what happens to the rasters after.

## The DAG's task order

```
0_check_forecast_rain --(rain)--> 1_trigger_simulation --> 2_download_results --> 3_calculate_depth
        |                                                          |                     |
        +--(dry)--> wait_before_next_rain_check                    v                     +--> 9_build_flood_tiles
                                                             3b_upload_netcdf_postgres   |
                                                                                         +--> 9b_load_depth_raster
```

`0b_ensure_schema` runs after `1_trigger_simulation` and feeds `3b_upload_netcdf_postgres`,
`9_build_flood_tiles`, and `9b_load_depth_raster`, since each needs its PostGIS tables to exist
first. It also creates the netcdf tables that `3b_upload_netcdf_postgres` writes, and it still
creates `flood_road_values`.

Tasks `9_build_flood_tiles` and `9b_load_depth_raster` name the run with
`flood_extent.run_ts_for_depth_dir`, the `stamp_key` of the earliest `depth_*.tif`. On 2026-09-24
the GeoJSON chain (`4_extract_geojson_full` to `8_upload_postgres`) left the DAG, per the plan
[[raster-first-flood-pipeline]]. Its last task was the only DAG task that wrote
`flood_road_values`, the table the routing backend reads. The DAG has no producer for
`flood_road_values` until Story 3 of [[raster-first-pipeline-stories]] lands, so do not deploy it
before then.

The DAG uses `VNContinuousTimetable` (`plugins/vn_timetable.py`) with `max_active_runs=1`, so the
next cycle starts immediately after the previous one finishes rather than on a fixed clock
schedule.

## The rain gate

`task_check_forecast_rain` calls `create_simulation.get_rain_forecast()` (Tomorrow.io, 15-minute
steps, `RAIN_LOOKAHEAD_HOURS` ahead) and `evaluate_rain_gate()`. A cycle only proceeds to
`1_trigger_simulation` if any forecast interval reaches `FLOOD_RAIN_THRESHOLD_MM_HR` (default 5
mm/h). Otherwise the `BranchPythonOperator` routes to `wait_before_next_rain_check`
(`RAIN_CHECK_INTERVAL_SECONDS`, default 900) and the cycle ends as a successful dry-cycle skip, not
a failure. `task_run_simulation` relies on this branch already having decided to run: a falsy
`sim_id` there always means a real 3Di failure, so it raises `AirflowException` rather than
`AirflowSkipException`, which would otherwise show identically green in the Airflow UI for both a
legitimate skip and an actual failure.

An operator can force a fixed rain rate for local testing with `FLOOD_TEST_RAIN_MM_HR`, which
bypasses the Tomorrow.io call and builds a deterministic rain series instead.

## Triggering the simulation

`create_simulation.run_forecast_process` builds the 3Di simulation from `TEMPLATE_ID` via the
official `threedi-api-client`'s `simulations_from_template`, using `FromTemplate` with
`clone_settings=True`, `clone_events=False`. Rain values (`build_rain_values`, converted from
mm/h to m/s with per-interval offsets) are pushed with
`simulations_events_rain_timeseries_create`, then the simulation is started with
`simulations_actions_create(sim_id, Action(name="start"))`.

`threedi_client.get_client()` is the single point of 3Di API auth config
(`THREEDI_API_HOST`, `THREEDI_API_PERSONAL_API_TOKEN`). This personal-API-token auth is not
compatible with the older `THREEDI_API_KEY` HTTP Basic auth some other scripts in this repo still
use; the two are not interchangeable.

### Hotstart and cold start

If `state_file_path` (`STATE_FILE`, `/opt/airflow/state/flood_system_state.json`) holds a
`last_saved_state_id` from a previous cycle, `run_forecast_process` sets `clone_initials=False` and
runs a hotstart from that saved state instead of a cold start from the template's own initial
conditions. Each run also registers a new saved state via
`simulations_create_saved_states_timed_create`, timed to `SIMULATION_DURATION` seconds into the
run and expiring after 1 day, so the next cycle has a state to hot-start from. `save_new_state` only
writes the new state ID to `state_file_path` after `monitor_simulation` confirms the run finished;
a crashed or timed-out run leaves the previous cycle's saved state in place for the next cycle to
use.

### Status polling

`monitor_simulation` polls `simulations_status_list` on a bounded loop: `POLL_TIMEOUT_SECONDS`
(default `SIMULATION_DURATION + 1800`), starting at `POLL_INTERVAL_SECONDS` (10s) and backing off
exponentially to `POLL_MAX_INTERVAL_SECONDS` (60s) on transient errors, giving up after 5
consecutive polling errors. A `finished` status returns success; `crashed`, `timeout`, or
`shut_down` return failure immediately rather than waiting out the timeout.

A 401 or 403 from any 3Di API call gets a distinct log line
(`_log_if_auth_expired`, `ALERT [3di-auth-expired, will-not-self-resolve]`), because an expired or
invalid token fails identically on every following cycle until it's rotated, unlike a timeout or a
transient error that might resolve on retry.

## Downloading the result

`task_download_result` calls `download_result.run_download`, which uses the client's
`simulations_results_files_download` endpoint plus `threedi_api_client.files.download_file`
(streaming, with retry) to save the first `.nc` result file under `RESULT_DIR`
(`data/mapping/results`).

## Turning the NetCDF into depth rasters

`task_calculate_depth` calls `netcdf_input.calculate_depth_from_download`, which drives
`calculate_depth.run_calculate_depth(grid_path, nc_path, dem_path, output_dir)`. Inputs are the
static `INPUT_GRID` (`data/mapping/inputs/gridadmin.h5`) and `INPUT_DEM`
(`data/mapping/inputs/dem.tif`).

`run_calculate_depth` reads the total timestep count from `GridH5ResultAdmin`, skips step 0 (3Di's
placeholder t=0 record, never a usable depth raster), and fans the rest out across a
`billiard.Pool` (a Celery-safe fork of `multiprocessing.Pool`) sized by `MAX_WORKERS`, defaulting to
`os.sched_getaffinity(0)`'s CPU count if unset. As read from `.env` on 2026-09-22, `MAX_WORKERS=1`
and `compose.yml`'s `AIRFLOW__CELERY__WORKER_CONCURRENCY` defaults to 1 (`AIRFLOW_WORKER_CONCURRENCY`
is not set in `.env`); an earlier plan file recorded `MAX_WORKERS=8` and
`AIRFLOW_WORKER_CONCURRENCY=2` as the checked-in defaults, so confirm current `.env` values before
relying on either concurrency figure.

Each worker (`process_single_step`) shells out to `threedidepth`'s own packaged CLI
(`threedidepth gridadmin results_3di dem waterdepth -s STEP`) rather than importing
`calculate_waterdepth()` in-process, matching how the rest of the pipeline (GRASS, `gdal_polygonize.py`,
`ogr2ogr`) already shells out instead of calling a Python API. A single `-s` value per call keeps
each output single-band; `validate_depth_raster` then rejects a corrupt or truncated file (under
`DEPTH_TIF_MIN_SIZE_BYTES`, default 1024) or one that's almost entirely NoData (over
`DEPTH_TIF_MAX_NODATA_RATIO`, default 0.999) before the raster gets timestamped and renamed to
`depth_<VN-local-date>_<VN-local-time>.tif`. `run_calculate_depth` collects every worker's result
string and raises if any timestep failed, so a cycle with a partial depth-tif set is never reported
as a success.

## Open items

- `.env`'s current `MAX_WORKERS=1` and `AIRFLOW_WORKER_CONCURRENCY` default of 1 look
  under-provisioned relative to what
  `artifacts/docs/claude-plan/calculate-depth-threedidepth-cli.md` describes as already checked in.
  Confirm which is actually current before assuming either concurrency figure without re-reading
  `.env`.
- No regression tests found for `create_simulation.py`'s hotstart/cold-start branching beyond
  `test_threedi_connection.py` (connectivity only) and `test/test.py` (see its own contents for
  coverage).
