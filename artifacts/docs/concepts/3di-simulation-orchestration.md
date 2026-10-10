---
date: 2026-09-22
type: concept
status: active
tags: [3di, airflow, simulation]
related: ["[[T3-Digital-Twin_Architecture]]", "[[calculate-depth-threedidepth-cli]]", "[[minio-flood-extent-pipeline]]", "[[raster-first-flood-pipeline]]", "[[road-segment-table]]", "[[flood-on-roads]]", "[[decision-log]]"]
last_updated: 2026-10-10
---

# 3Di simulation orchestration

`dags/flood_mapping_dag.py` runs one cycle every 15 minutes: check the rain forecast, decide whether to
run a 3Di simulation, run it, download the result, turn it into depth rasters, and hand those to
the flood-extent tile task, the depth raster load, and the flood-on-roads task. This page covers the first three steps,
through the depth raster. See [[minio-flood-extent-pipeline]] for what happens to the rasters after.
The section "The manual two-event test DAG" covers a DAG that runs the same steps on synthetic rain.

## The DAG's task order

```
0_check_forecast_rain --(dry state)--> run ends, every later task skipped
        |
   (rain, or a flood still stands)
        v
1_trigger_simulation --> 2_download_results --> 3_calculate_depth --> 3b_publish_depth_files
        |                        |                      |                  (asset event, starts flood_tiles)
        |                        v                      +--> 9b_load_depth_raster
        |               2b_archive_results --> 2c_archive_done
        v
0b_ensure_schema
```

The diagram leaves out the edges from `0b_ensure_schema` to `3b_publish_depth_files` and `9b_load_depth_raster`, and from `2c_archive_done` to `3b_publish_depth_files`. The DAG has 9 tasks. The tile build `9_build_flood_tiles` left the DAG for `flood_tiles`, which runs on the asset `3b_publish_depth_files` emits ([[US-103-move-the-flood-tile-build-into-its-own-dag|US-103]]). Task `3b_upload_netcdf_postgres` left the DAG on 2026-10-10 ([[US-095-retire-the-netcdf-values-ingest|US-095]]). Since 2026-10-07 (commit
`77169c3` on the branch `modular`) the routing tasks are in their own DAG, `routing_adapter`,
described in the next section. `routing_adapter` is unpaused on the server (checked 2026-10-08), and
`artifacts/TODOS.md` records it running there from 2026-10-07 16:00 +07.

`0b_ensure_schema` runs after `1_trigger_simulation` and feeds `3b_publish_depth_files` and
`9b_load_depth_raster`, since each needs its PostGIS tables to exist
first. It creates the three empty TimescaleDB tables, `flood_road_values` with its `segment_id` column, the flood
extent tables, the depth raster tables, and `road_segment` and `graph_edge`, which only
`routing_adapter` uses (`task_ensure_schema`). It runs before `9b_load_depth_raster`, so those tables exist before the first asset event.

Task `9b_load_depth_raster` declares the asset `FLOOD_DEPTH_RASTER` (`dags/core_assets.py`) as an
outlet and sets `run_ts` in the event's `extra`. Airflow emits the event only when the task
succeeds, so a dry cycle emits none. The event is the signal that a run's depth tiles are in
`flood_depth_raster_tile`. See [[core-output-contract]], "Readiness".

Tasks `3b_publish_depth_files` and `9b_load_depth_raster` name the run with
`flood_extent.run_ts_for_depth_dir`, the `stamp_key` of the earliest `depth_*.tif`. On 2026-09-24
the GeoJSON chain (`4_extract_geojson_full` to `8_upload_postgres`) left the DAG, per the plan
[[raster-first-flood-pipeline]].

## The routing_adapter DAG

`dags/routing_adapter_dag.py` has the schedule `[FLOOD_DEPTH_RASTER]`, so it runs after each
`9b_load_depth_raster` success. It has three tasks. All use the Airflow pool `routing_adapter`,
which has one slot, so routing holds at most one worker slot and never two writers on
`road_segment`. Someone creates the pool once by hand (README, "Create the Airflow pools").
Nothing in `flood_mapping_full` waits for these tasks, so a failure here leaves the core run
green and does not block the next slot from hotstarting.

```
load_road_segments --> flood_on_roads

9c_build_edge_depth_table
```

`published_run_ts` gives each task its run. It reads `run_ts` from the triggering asset events. If
the scheduler folds several events into one run, the newest `run_ts` wins, the same rule as the
`latest` pointer of the edge depth table. A manual run has no triggering event and reads the newest
event that `9b_load_depth_raster` ever emitted.

`load_road_segments` makes `road_segment` match the roads file each cycle. An unchanged file reports
0 inserted, 0 updated, and 0 deleted. A bad file fails the task before anything is written. See
[[road-segment-table]].

`flood_on_roads` waits for `load_road_segments`. It samples the run's tiles along each road piece
and writes `flood_road_values`, the table the routing backend reads. It replaced the GeoJSON chain
as the writer on 2026-09-25. See [[flood-on-roads]].

`9c_build_edge_depth_table` has no upstream task, because the event already says the tiles are
loaded. It has the highest priority in the pool, so it takes the slot before the road tasks. It
samples the run's tiles along every GraphHopper edge and writes `<run>.bin`, the edge depth table,
into `EDGE_TABLE_DIR`. It reads the export of the graph's edges from `EDGE_EXPORT_DIR`, then
publishes the table (US-042): `latest` points at it, only forward, and the newest
`EDGE_TABLE_KEEP_RUNS` stay. `EDGE_TABLE_DIR` is the Docker volume `edge-depth-tables`. The limit
of `US-045` is that it ends within 5 minutes of `3_calculate_depth`. The one real run measured so far
ended 8.21 minutes after it, which one run cannot tell apart from the catch-up of a new DAG. `US-045`
stays open until the 12-hour replay of 2026-10-08 supplies more runs (`artifacts/TODOS.md`). See [[edge-depth-table-format]], "Build task".

**Schedule.** The DAG runs on the cron `*/15 * * * *` with `catchup=False` and `max_active_runs=2`
(`dags/flood_mapping_dag.py`), following the design in [[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]] and decision D-014 in [[decision-log]]. The repository
has no `plugins/` directory and no custom timetable. A run can last about 15 minutes, so the next
slot's run may start while the previous one finishes. The two runs share no files. Each download goes
to `RESULT_DIR/<sim_id>/`, and each reprojected raster is named after its `run_ts`.

Each run starts at its 15-minute clock slot, not at `now()`. `create_simulation.clock_slot()` floors the
time to the slot, and `run_forecast_process` sets the 3Di start time and the rain series from that slot
(`dd78bcb`, `09e8650`, `00b42b0`). `choose_saved_state` hotstarts from the saved state whose `valid_at`
equals the slot, or the newest state at most two cycles older, else it cold starts. See
[[BL-009-hotstart-state-saved-at-end-of-run|hotstart-state-saved-at-end-of-run]]. Concurrency for overlapping runs is covered in
[[BL-013-flood-mapping-full-worker-concurrency-serializes-runs|flood-mapping-full-worker-concurrency-serializes-runs]]. The plan is
[[fifteen-minute-cycle-tiles-and-histogram]]. The user unpaused `flood_mapping_full` at about
15:05 +07 on 2026-10-08 for the 12-hour replay (`artifacts/TODOS.md`). Whether the DAG stays unpaused
after the replay is unverified. The server also had the test DAGs `calculate_depth_manual_test` and
`flood_forecast_consecutive_state_test` (both `schedule=None`) and `zz_cold_start_probe` unpaused on
2026-10-08. `zz_cold_start_probe` has no file in `dags/` in the repository, so its schedule is unverified.

## The rain gate

`task_check_forecast_rain` calls `create_simulation.get_rain_forecast()` (Tomorrow.io, 15-minute
steps, `RAIN_LOOKAHEAD_HOURS` ahead). The source is Tomorrow.io because NCHMF did not approve API
access (D-013 in [[decision-log]]). and `evaluate_rain_gate()`. A cycle proceeds to
`1_trigger_simulation` if any forecast interval reaches `FLOOD_RAIN_THRESHOLD_MM_HR` (default 5
mm/h). Below that, `scripts/standing_flood.py` reads the newest 5 runs of `flood_road_values` (US-101,
[[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands|BL-028]]). The run proceeds while a recent run (under 45 minutes old) is in progress and either one of those 5 runs has a deepest value of 5 cm or more
(`FLOOD_DRY_DEPTH_M`, 0.05 m), or some rain is forecast. So the 5 mm/h gate applies only from a dry state, and a running simulation stops once the newest 5 runs are under 5 cm and the forecast is 0.
On 2026-10-10 the rule ran the 4 slots of the event window that the 5 mm/h gate alone would have skipped ([[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands|BL-028]], resolved). Otherwise the `BranchPythonOperator` returns `None`, which skips every later task, and the
run ends as a successful dry-state skip, not a failure. `task_run_simulation` relies on this branch already having decided to run: a falsy
`sim_id` there always means a real 3Di failure, so it raises `AirflowException` rather than
`AirflowSkipException`, which would otherwise show identically green in the Airflow UI for both a
legitimate skip and an actual failure.

An operator can force a fixed rain rate for local testing with `FLOOD_TEST_RAIN_MM_HR`, which
bypasses the Tomorrow.io call and builds a deterministic rain series instead.

An operator can also replay a recorded event. `FLOOD_TEST_RAIN_CSV` names a file of
`offset_minutes,precipitation_mm_hr` rows, 30 minutes apart, and `FLOOD_TEST_RAIN_START` is the UTC
time of offset 0. Each run reads its own 2-hour lookahead from the event (`scripts/rain_replay.py`,
`replay_intervals`), and each 30-minute rate holds for both of its 15-minute intervals. The rate is 0
mm/h before the start and after the last row. Setting only one of the two variables, or setting either
with `FLOOD_TEST_RAIN_MM_HR`, raises a `ValueError`. The committed event is
`scripts/rain_events/hanoi_20251005_48h.csv`, the Hanoi rain of 2025-10-05T22:30Z to 2025-10-07T22:30Z
(246.8 mm, peak 56.48 mm/h). On 2026-10-02 the server's `.env` set `FLOOD_RAIN_THRESHOLD_MM_HR=0.01`, so all 192 runs of its window simulate. At 5 mm/h, 104 of its 192 runs simulate. The rain gate skips the
rest as dry cycles, and a skipped run counts as a success for the cold start rule. `python3 scripts/rain_replay.py preview EVENT START_UTC THRESHOLD` lists the chains of simulating runs, with a cold start for a run whose last simulating slot is more than 4 slots earlier. Three more subcommands need no Docker: `next-slot NOW_UTC LEAD_MINUTES`, `check EVENT START_UTC THRESHOLD` (refuses an event that does not load, a start off the 15-minute grid, or a gate that no run reaches), and `status [--expect-mode MODE] [--expect-start START_UTC]` (reads the four rain variables from the environment and reports `live`, `replay`, or `fixed-rate`). On the server, `scripts/rain_env/replay.ps1` has `start -Event PATH`, `stop`, and `status`. `start` picks the next slot at least 30 minutes ahead, saves the prior values to `.env.rain-replay.json`, edits `.env`, recreates only the worker, and reads the setting back from inside the worker. It does not unpause the DAG. Built on `modular`. `start` ran on the server on 2026-10-08 with `hanoi_20260916_storm.csv` (12 hours, gate 5 mm/h, 42 simulating runs) and the read-back inside the worker matched. `stop` ran on 2026-10-10 at 18:49 +07 and read back `mode live` (`US-089`, [[rain-replay-test-environment]], decision D-012 in [[decision-log]]).
The 2026-10-10 replay ran 55 runs from 04:45 to about 18:15 +07, and all of them ended `success` ([[US-102-replay-the-storm-with-the-us-101-fix-to|US-102]]).
The server's git remote for this repository is `alice`, not `origin`. See
[[us-063-realistic-rain-replay-for-us-037-and-us-034]].

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

### Cold start after a broken chain

Since 2026-10-02, `task_run_simulation` asks `ti.get_dr_count` for the DAG runs at exactly the previous
slot (slot minus 15 minutes) in state `success` or `running`. With none, `hotstart_policy.should_hotstart`
returns false, and the run passes `hotstart=False` to `run_forecast_process`. That run starts cold from
the template's initial conditions but still registers its timed saved states, so the next run can
hotstart from it. The reason is that stopping an Airflow run does not stop its 3Di simulation, whose
timed saved states stay in the state file. `choose_saved_state`'s 30-minute window can then find one
after a restart, and the run would hotstart from a storm that kept growing. The rule is on by default,
and `FLOOD_COLD_START_AFTER_BREAK=0` turns it off. The trigger log prints a `Chain check` line with the
verdict. Checked live on 2026-10-02: the first run after a restart logged `cold start forced`, and the
four runs after it logged `hotstart allowed` and `[Hotstart, exact]`.
On 2026-10-10 the replay logged `[Hotstart, exact]` in 57 trigger logs and `[Coldstart]` in none, and the only forced cold start was the 04:00 run that began the chain ([[US-102-replay-the-storm-with-the-us-101-fix-to|US-102]]).
A failed 3Di trigger also breaks
the chain, so the next run cold-starts instead of using the two-cycle backup state.

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

Rana keeps a simulation's result files for one month (stated by the user on 2026-10-10).
A past run can therefore be rebuilt without a new simulation until then.
Take its `sim_id` from the `1_trigger_simulation` XCom, call `download_result.run_download`, and run `calculate_depth.run_calculate_depth` on the file.
The local `depth.tif` files under `data/mapping/output_depths` are a cache, and the 24-hour cleanup of `9_build_flood_tiles` (now in `flood_tiles`) may delete them.
A saved state is different.
`create_simulation.py` registers each one with an expiry of one day, so a hotstart is possible only from a run less than a day old.
A slot that never ran has no result to download, and only a new simulation can fill it.

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

Each step reads the DEM, the grid, and the results file. On the Windows bind mount, 8 steps at once took
368.6 s, and from the container's local disk they took 148.6 s (experiment of 2026-10-01). So
`run_calculate_depth` copies the grid and DEM into `DEPTH_LOCAL_INPUT_DIR` (default `/tmp/depth_inputs`,
reused while size and mtime match) and the results file into a per-run temp folder, through
`scripts/depth_inputs.py`'s `localize_input`. A failed copy falls back to the original path. On the live
DAG the depth task fell from 6.8 to 7.5 minutes to 3.2 to 3.9 minutes.

## The manual two-event test DAG

`dags/flood_forecast_state_test_dag.py` defines `flood_forecast_consecutive_state_test`, a DAG you
trigger by hand to test a hotstart on a dry day. It has no schedule and no rain gate. Event 1 is
20 mm/h for 2 hours from a cold start, and it saves a 3Di state at its end. Event 2 is 5 mm/h for
2 hours, starts when event 1 ends, and hotstarts from that saved state. The DAG uses its own state
file (`/opt/airflow/state/flood_state_test.json`) and its own folders under
`/opt/airflow/data/mapping_state_test`, and it deletes its state file before event 1 so every run
starts cold.

After each event's depth calculation, the DAG runs the same steps as `flood_mapping_full`:

```
0_ensure_schema --> load_road_segments

1_trigger_event1 --> 2_download_event1 --> 3_calculate_depth_event1 --> 3b_build_tiles_event1
                             |                        |
                             |                        +--> 3c_load_depth_raster_event1 --> 3d_flood_on_roads_event1
                             v
    4_trigger_event2 --> 5_download_event2 --> 6_calculate_depth_event2 --> 6b_build_tiles_event2
                                                          |
                                                          +--> 6c_load_depth_raster_event2 --> 6d_flood_on_roads_event2
```

The diagram leaves out three groups of edges. `0_ensure_schema` feeds `load_road_segments` and every
`b`, `c`, and `d` task. `load_road_segments` feeds both flood-on-roads tasks.
`3b_build_tiles_event1` and `3c_load_depth_raster_event1` feed `6_calculate_depth_event2`.
`test/test_flood_state_test_dag_graph.py` holds the exact task and edge sets.

`6_calculate_depth_event2` waits for event 1's tile build and raster load as well as its own
download, so the heavy depth calculation never runs beside either of them.
`0_ensure_schema` creates the same tables as `flood_mapping_full`'s `0b_ensure_schema`, including
the netcdf tables. The DAG has no netcdf upload task, so synthetic simulations never reach the real
netcdf tables.

Both events publish under one run name, the stamp of event 1's earliest depth file. See D-007 in
[[decision-log]]. The map's timeline lists the timesteps of the newest run only, so one run name
shows the whole four hours, and event 1 stays on the timeline after event 2 publishes. Running
each step twice under one run name is safe for these reasons:

- `publish.publish_run` writes one folder per timestep under `runs/<run_ts>/`, and the two events
  have different timesteps. The DAG passes `keep_runs=1000`, so its pruning deletes nothing.
- `raster_load.load_run` deletes and inserts one timestep at a time, so event 2's load leaves event
  1's timesteps alone. The DAG passes `keep_runs=1000`, so it never prunes production tiles.
- `flood_on_roads.compute` recomputes every timestep loaded for the run. Event 2's task rewrites
  event 1's timesteps with the same depths, plus a 0 row for each piece that only event 2 floods.

A shared timestep would break the first point, because `publish_run` would leave event 1's tiles
and polygons in the folder. That happens only when `SIMULATION_DURATION` is longer than event 1's
2-hour rain window. The event 2 tasks check for it and fail before they write anything.

The DAG writes `flood_road_values` in place, so routing uses the test event until a newer
production run replaces it. The DAG docstring lists every table and MinIO prefix a run writes, and
the SQL that removes them.

The test run's timesteps start at its trigger time, so its newest timestep is about 4 hours after
the trigger. The frontend opens in flood mode only when the newest timestep is within 45 minutes of
now (see [[minio-flood-extent-pipeline]]). Until about 3 hours 15 minutes after the trigger, the map
therefore opens in map mode, and the tester switches to flood mode by hand.

## Open items

- `.env` on the Mac, read on 2026-10-08, sets `MAX_WORKERS=1` and no `AIRFLOW_WORKER_CONCURRENCY`, so
  the `compose.yml` default of 1 applies (line 28). `artifacts/archive/plans/calculate-depth-threedidepth-cli.md`
  recorded `MAX_WORKERS=8` and `AIRFLOW_WORKER_CONCURRENCY=2` as checked in. The server's `.env` is
  unverified, so confirm it before relying on either concurrency figure.
- `test/test_create_simulation_cycle.py` tests the hotstart and cold-start branching of
  `run_forecast_process` (exact state, fallback up to two cycles old, older state as a cold start), and
  `scripts/test_hotstart_policy.py` tests `should_hotstart`. `test/test.py`, a local end-to-end harness
  for the retired GeoJSON chain, was removed on 2026-09-29.
