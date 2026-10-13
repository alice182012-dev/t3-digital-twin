---
date: 2026-09-23
type: concept
status: active
tags: [architecture, source-of-truth, floodnav]
related: ["[[T3-Digital-Twin_Architecture]]", "[[architecture-block-diagram]]", "[[minio-flood-extent-pipeline]]", "[[graphhopper-backend]]", "[[storage-backend-django-layer]]", "[[3di-simulation-orchestration]]", "[[routing-depth-threshold-model]]", "[[core-output-contract]]", "[[edge-depth-table-format]]", "[[sticky-routing-reference]]", "[[flood-on-roads]]", "[[decision-log]]", "[[SP-01-prd-and-backlog|sprint-plan]]", "[[SP-02-routing-engine-foundations|sprint-plan-2]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[analysis-service]]", "[[test-dataset]]", "[[timescaledb-schema]]", "[[flood-metric-extractor]]"]
last_updated: 2026-10-13
---
# FloodNav architecture

Working copy of `artifacts/raw/SW Architecture.md`, rewritten into the C4-style template at
`artifacts/raw/ideas/architecture.md-howto/Architecture template.md` (Project structure, System
context, Container diagram, Core components, Data stores, External integrations, Deployment,
Security, Development and testing, ADRs, Roadmap, Glossary). Two early decisions are folded in
directly: map tiles moved from raster PNG to vector polygons (ADR-001), and routing moved from
Valhalla to GraphHopper (ADR-002).

On 2026-10-13 this file was synced with the code on the branch `modular`.
The sync read `compose.yml`, `dags/`, `scripts/`, `floodmap/graphhopper-flood-road/backend/`, and `analysis-service/` in the working tree of that day, where `git status` showed no change to code.
The branch `main` does not contain most of what this file marks Built.
`git log --oneline main..modular | wc -l` printed 489 on 2026-10-13 (212 on 2026-10-08).
Facts about the server come from the daily logs of 2026-10-09 to 2026-10-13 and from the concept pages.
The sync did not read the server again, so each server fact carries the date of the log that recorded it.

Every component carries one of four markers:

- **Built.** A `compose.yml` service, a DAG task, a script that a DAG calls, or an endpoint exists at
  the branch `modular` on the sync date above and the code was read.
- **Built, not scheduled.** The code exists, and no DAG, service, or endpoint calls it.
- **Designed, not built.** The original whiteboard design specifies it, and no code for it exists in
  this repository.
- **Retired** or **Dropped.** Retired means it was built and then removed. Dropped means the design
  specified it and the user decided not to build it.

A fact that the code cannot show is marked "unverified". Where the build differs from the original
design, a short "Original design" note keeps the intent, because this file is the only record of it.

## 1. Project structure

```
t3-digital-twin/
├── dags/                          # Airflow DAGs
│   ├── flood_mapping_dag.py       # DAG flood_mapping_full, every 15 minutes: rain gate, 3Di run, archive, depth, raster load
│   ├── flood_tiles_dag.py         # DAG flood_tiles, runs on the asset flood_depth_files: task 9_build_flood_tiles
│   ├── routing_adapter_dag.py     # DAG routing_adapter, runs on the asset flood_depth_raster_tile: task 9c_build_edge_depth_table
│   ├── flood_history_dag.py       # DAG flood_history, runs on the asset edge_depth: depth_history and history_moment
│   ├── core_assets.py, core_paths.py   # The three Airflow assets, and the folders that flood_mapping_full and flood_tiles share
│   ├── flood_forecast_state_test_dag.py   # Manual two-event hotstart test (flood_forecast_consecutive_state_test)
│   ├── calculate_depth_manual_test_dag.py # Manual depth test (calculate_depth_manual_test)
│   └── initial_wl_dag.py, dummy_initial_wl_dag.py, manholes_dag.py   # Older water-level DAGs, not part of the 15-minute cycle
├── scripts/                       # Python pipeline code, run by Airflow tasks
│   ├── create_simulation.py       # Rain gate, 3Di run, saved states (hotstart), cold start
│   ├── threedi_client.py, download_result.py, netcdf_input.py, depth_inputs.py, calculate_depth.py, hotstart_policy.py
│   ├── standing_flood.py, stale_run.py, forecast_mode.py, archive_results.py   # Standing-flood rule, stale-run guard, forecast mode row, results archive
│   ├── database/                  # DDL scripts, run_output.py, demo_pin.py, reader role scripts (create_routing_reader_role.py, create_timescale_reader_role.py, create_analysis_schema.py, roles.py)
│   ├── flood_extent/              # flood_extent.py (GRASS raster to polygon), publish.py (MinIO and PostGIS), raster_load.py
│   ├── edge_depth/                # build_edge_depth.py, edge_depth_rows.py, publish_edge_depth.py, edge_depth_table.py, graph_edges.py, check scripts
│   ├── flood_history/             # load_run.py (edge_depth into depth_history and history_moment)
│   ├── flood_metrics/             # metrics.py, extract_run.py (no DAG task calls them)
│   ├── testdata/                  # restore_snapshot.py, rebuild_tiles.py, build_history_and_metrics.py, run_db_tests.py (the test dataset)
│   ├── routing_reference/         # Slow reference and checker for sticky closure routing
│   ├── routing_experiments/       # Harness of the routing paper experiments
│   ├── routing_proof/             # Server proof of the routing engine, rollout.ps1
│   ├── backend_soak/, pipeline_margins/, storage_check/   # Soak, timing, and storage checks
│   ├── rain_replay.py, rain_env/replay.ps1, rain_events/  # Rain replay tooling and event files
│   ├── render_todos.py            # Renders artifacts/TODOS.md from the vault
│   ├── initial_wl/, manholes/     # Water-level scripts used by the older DAGs
│   ├── merge_to_minio.py          # Leftover of the GeoJSON chain, no file imports it
│   └── test_*.py                  # Tests of the scripts at the top level
├── analysis-service/              # Image, requirements, app/server.py, and tests of the analysis container
├── floodmap/
│   ├── graphhopper-flood-road/    # backend/ (server.py and one module per endpoint), graphhopper/ (config.yml, custom_model files), scripts/flood_utils.py
│   └── graphhopper-maps/          # Frontend: vendored GraphHopper Maps fork, src/floodmap/, nginx.conf
├── java/time-aware-routing/       # Maven module and Dockerfile for the time-aware GraphHopper image
├── minio_custom/                  # storage-backend (Django, JWT, boto3) and storage-frontend (Vite, React)
├── test/                          # Pytest suite for the DAGs and the 3Di scripts, with conftest.py
├── pytest.ini                     # Python path of the suites (US-137)
├── marie-curie/                   # Disposable scratch space, not tracked by git except its README
├── artifacts/                     # This Obsidian vault
├── .github/workflows/             # CI: java-module.yml, flood-areas-test.yml, restore-snapshot-test.yml
├── Dockerfile, requirements.txt   # Airflow image (Airflow 3.1.7, GDAL 3.6.2, GRASS GIS, Tesseract)
└── compose.yml                    # Full service definition, runs on the remote Docker host
```

Original design: the scratch folder was named `einstein/`.
It was renamed to `marie-curie/` on 2026-09-23.
The retired folder `floodmap/valhalla-flood-road-test/` was deleted the same day (ADR-002).
The GeoJSON scripts `scripts/extract_geojson.py` and `scripts/mapping/*` were deleted on 2026-09-29.
The second sampler was deleted on 2026-10-13: `scripts/flood_roads/`, `scripts/roads/`, and `scripts/database/geojson_to_pg.py`, with the table creation scripts for `road_segment` and `flood_road_values` (ADR-014).
The NetCDF ingest (`scripts/database/netcdf_to_pg.py` and the task `3b_upload_netcdf_postgres`) was deleted on 2026-10-09 (ADR-007).
To regenerate this tree, run `ls` in each folder and `git ls-files | cut -d/ -f1-2 | sort -u`.

## 2. System context

**FloodNav** is a flood navigation and warning platform for Hanoi. The built part is a pipeline that
runs a 3Di hydrodynamic simulation every 15 minutes when rain is forecast or a flood still stands, publishes flood depth as map tiles, depth rasters, per-edge depth rows, an edge depth table and a depth history, and serves vehicle-aware routes over them.
Original design: refresh every 30 minutes, with forecast histograms and push alerts. The default cadence
is now 15 minutes, and the histograms and alerts are not built.

### Actors and external systems

| Actor or system | Relationship | Status |
| --- | --- | --- |
| Hydraulic engineer | Builds the 3Di schematisation, the calculation-node mapping, and the simulation templates. One-time manual setup, versioned in a geopackage. | Built (manual, outside the automated pipeline) |
| 3Di (`api.3di.live`) | Cloud hydraulic simulation engine. The pipeline creates a simulation from the template `TEMPLATE_ID`, uploads the rain as a time series, hotstarts from a saved state, and downloads the first `.nc` result file. See [[3di-simulation-orchestration]]. | Built |
| Tomorrow.io | Rain forecast at 15-minute steps, read by `create_simulation.get_rain_forecast`. It feeds both the rain gate and the 3Di rain input. | Built. Original design: NCHMF supplied the forecast. |
| Trung tâm dự báo KTTV Quốc Gia (NCHMF) | Rainfall forecast (GRIB2 or NetCDF), polled once per cycle. | Designed, not built. A search of `dags/`, `scripts/`, and `compose.yml` finds no reference to it. The vault records no decision to use Tomorrow.io instead. |
| Gauge network water levels | Original design: read at cycle start to hot-start the simulation from observed levels. The built cycle hotstarts from a 3Di saved state instead (`choose_saved_state`). | Designed, not built for the 15-minute cycle |
| Hanoi drainage company pages (`thoatnuochanoi.vn`) | `dags/manholes_dag.py` (`manholes_waterlevel_rain_pipeline`, every 2 hours) scrapes water-level and rain pages with Tesseract OCR and uploads CSV files to the `manholes-data` bucket. | Built as its own DAG. Nothing in `flood_mapping_full` reads the output. The DAG is unpaused on the server (checked 2026-10-08), so it runs every 2 hours. |
| NASA IMERG | Satellite rain used offline to cut the replay event `scripts/rain_events/hanoi_20260916_storm.csv` (`marie-curie/us-088/`). | Built as a one-off tool, not a runtime dependency |
| Photon (`photon.komoot.io`) | Place search and reverse geocoding for `floodmap-backend` (`place_search.py`, `PHOTON_BASE_URL`). The instance is public and slow. On 2026-10-13, Photon took 4 to 6.5 s to answer, and 11 of 12 calls of `GET /places/reverse` timed out at the 5 s limit (`PHOTON_TIMEOUT_SECONDS`). A Photon instance for Vietnam next to the backend is `US-141`, on hold. See [[BL-021-place-name-slow-after-map-tap\|BL-021]]. | Built, with an open blocker (`BL-021`, P3) |
| Industry analysis applications | Read the flood results and the depth history through their own roles, in the container `analysis` (section 4.14). | Partly built. The container, its roles, and `GET /health` exist (`US-109`). No analysis application runs in it yet. |
| Citizen (mobile or web app) | Views the flood map and plans a route. | Partly built. `flood-routing-frontend` is the web slice (section 4.9). Alerts and community reports are Designed, not built. |
| City council (dashboard) | Monitors city flood status, dispatches response, logs decisions. | Designed, not built |
| Ride-hailing services (GrabBike, XanhSM, Be) | Consume flood data programmatically for fleet routing (Phase 3 partner API). | Designed, not built, and its extension point (a partner MVT endpoint) is not built either |
| FCM and APNs | Push alert delivery. A one-way, asynchronous channel with no delivery visibility, flagged in the original design as a reliability risk that needs a fallback. | Designed, not built. No alert engine exists to call it. |

### Design rationale carried forward

- **Users are segmented by decision type, not just by role.** Citizens make immediate personal safety
  decisions (travel or not, which route, stay or go). The council coordinates the city-wide response
  (dispatch, public announcements, service accessibility). Ride-hailing partners consume a data feed
  programmatically and were never meant to use a FloodNav UI.
- **Community reports are isolated from the simulation model by design**, so live citizen feedback
  cannot contaminate the hydrodynamic results that emergency decisions rest on. Their main long-term
  value is post-event model calibration, once verified separately.
- **FCM and APNs are modeled as external systems that FloodNav calls**, because the delivery contract is
  one-way with no guarantee. This is why the design requires an in-app poller as a fallback (section 4.9)
  and does not rely on push alone for safety-critical alerts.
- **A fast-track mode** is specified: gauge rise above 5 cm in 15 minutes, an NCHMF forecast above
  70 mm/hr within 2 hours, 3 or more community flood reports in 30 minutes, or a manual operator
  override. It reverts to the default cadence after two calm cycles. Designed, not built. Original
  design: the default cadence was 30 minutes, so fast-track meant 15 minutes. The default is now
  15 minutes, so the mode has no faster cadence to switch to. The triggers are unbuilt.

## 3. Container diagram

Services in `compose.yml` on the sync date above. [[architecture-block-diagram]] draws them.

| Container | Tech | Status | Responsibility |
| --- | --- | --- | --- |
| `airflow-apiserver`, `airflow-scheduler`, `airflow-dag-processor`, `airflow-worker`, `airflow-init`, `airflow-trigger-flood-mapping` | Apache Airflow 3.1.7, CeleryExecutor | Built | Orchestrate `flood_mapping_full`, `flood_tiles`, `routing_adapter`, and `flood_history`. `airflow-trigger-flood-mapping` runs `airflow dags unpause flood_mapping_full` once at startup. The owner paused `flood_mapping_full` on 2026-10-10 and last unpaused it at 09:39:53 UTC on 2026-10-13 (log of 2026-10-13). The logs do not list the other DAGs after 2026-10-08, so their state since then is unverified. On 2026-10-08 the server had these DAGs unpaused: `flood_mapping_full`, `routing_adapter`, `calculate_depth_manual_test`, `flood_forecast_consecutive_state_test`, `manholes_waterlevel_rain_pipeline`, and `zz_cold_start_probe`. It had `flood_forecast_pipeline_test`, `flood_initial_wl_pipeline`, and `initial_wl_dummy_pipeline` paused. `calculate_depth_manual_test` and `flood_forecast_consecutive_state_test` have `schedule=None`, so they run only when triggered. `zz_cold_start_probe` has no file in `dags/` in this repository, so its schedule is unverified. The plan for `US-063` calls it an unscheduled probe with 0 runs on 2026-10-02. |
| `airflow-postgres`, `airflow-redis` | PostgreSQL 16, Redis 7.2 | Built | Airflow's metadata database and Celery broker. Not the multi-role Redis described later in this table. |
| `graphhopper` | Image `graphhopper-time-aware:local`, built from `java/time-aware-routing` on the host | Built | Flood-weighted routing engine with the time-aware search (ADR-002, ADR-008). Replaced the Valhalla design. The engine was deployed and tested on the server on 2026-10-07. The default of `TIME_AWARE_ROUTING` in `compose.yml` is still `false`. The server `.env` sets it to `true` since 2026-10-12 (D-034, read back that day), so `floodmap-backend` sends live routes to the engine (section 4.5). In `DEMO` mode the route skips the engine (ADR-015). |
| `floodmap-backend` (`floodmap/graphhopper-flood-road/backend/server.py`) | Python standard library `ThreadingHTTPServer`, psycopg2 pool | Built | Derives GraphHopper's `custom_model` from the PostGIS tables `edge_depth` and `graph_edge`, proxies GraphHopper, and serves `/flood/*`, `/route`, and `/route/departures`. Reads `forecast_mode` and `demo_pin` to serve the three map modes (ADR-015). |
| `flood-routing-frontend` (`floodmap/graphhopper-maps`) | TypeScript, vendored GraphHopper Maps fork, nginx | Built | Map and routing UI. Renders vector `.pbf` tiles from MinIO and sends route requests. |
| `minio`, `minio-init` | MinIO `RELEASE.2025-09-07T16-13-09Z` | Built | Buckets `initial-wl`, `manholes-data`, `flood-extent`. Replaced the S3 and CloudFront design (ADR-001). |
| `storage-postgres` | PostgreSQL 17 with PostGIS 3.5 (`imresamu/postgis:17-3.5`) | Built | The contract tables (section 4.10), `graph_edge_export`, `flood_segment_metrics`, and `minio_custom`'s role and access tables. Schema `analysis` for the analysis container. All pipeline tables stay in schema `public` (ADR-016). The test databases `minio_custom_test` and `flood_metrics_test` live beside the production database (ADR-017). |
| `timescaledb` | TimescaleDB 2.30.1 on PostgreSQL 17 | Built | The tables `depth_history` and `history_moment`, written by `flood_history` (ADR-019). The NetCDF values it held from 2026-10-05 were retired on 2026-10-10 (ADR-007). The histogram tables of the original design stay empty (ADR-005). |
| `storage-backend`, `storage-frontend` (`minio_custom/`) | Django REST with JWT, Vite and React | Built | Human-operator UI over MinIO buckets. Separate from the pipeline's own bucket use. See [[storage-backend-django-layer]]. |
| `analysis` (`analysis-service/`) | Python standard library `ThreadingHTTPServer`, psycopg2, own image and `requirements.txt` | Built | Container for the industry analysis applications. Own credentials only: `analysis_reader` and `analysis_owner` on `storage-postgres`, `analysis_timescale_reader` on `timescaledb`. It serves `GET /health` and nothing else (section 4.14). Publishes port 8020 on `127.0.0.1`. |
| Docker volume `edge-depth-tables` | Docker named volume | Built | The edge depth files. The Airflow worker writes. `graphhopper` and `floodmap-backend` mount it read-only (ADR-009). |
| Archive folder (`ARCHIVE_HOST_PATH`) | Bind mount of the worker, `D:\airflow_new_data\archive` on the server | Built | `results_3di.nc` and `run_record.json` of each real-rain run, for analysis after a storm (ADR-020). |
| Redis (task queue, pub-sub bus, short-TTL cache) | Redis | Designed, not built | Would fan out postprocessing work, publish cycle-completion events, and cache API responses. |
| Citizen-facing REST API, as a container distinct from `floodmap-backend` | n/a | Designed, not built | `floodmap-backend` covers routing, map listing, point and route depth. Alerts, community reports, and the dashboard endpoints do not exist. |
| User Location Store | n/a | Designed, not built | User GPS and consent mode. |
| Mobile app, city council dashboard | n/a | Designed, not built | See sections 4.9 and 4.10. |

**Key data flows (built).** Tomorrow.io feeds the rain gate and the 3Di run in `flood_mapping_full`.
The gate also stays open while an earlier flood still stands on the roads (section 4.1).
Each decision writes one row of `forecast_mode`.
`3_calculate_depth` produces `depth_*.tif` (8 per run), and the worker archives `results_3di.nc` of a real-rain run.
Two tasks read the depth files.
`3b_publish_depth_files` emits the asset event `flood_depth_files`, and that event starts the DAG `flood_tiles`, whose task `9_build_flood_tiles` writes `flood_extent_polygon`, `flood_extent_step`, and the `.pbf` tiles in MinIO.
`9b_load_depth_raster` writes `flood_depth_raster_tile` and emits the asset event `flood_depth_raster_tile`.
That event starts `routing_adapter`, whose one task `9c_build_edge_depth_table` writes the edge depth file, the `edge_depth` rows, and the `edge_depth_run` registry row.
Task `9c` then emits the asset event `edge_depth`, and that event starts `flood_history`, which copies the run into `depth_history` and `history_moment` in TimescaleDB.
`floodmap-backend` reads the contract tables as the read-only role `routing_reader`, and reads the edge depth file.
It serves graded routes, departure advice, depth lookups, and the map mode.
The `analysis` container reads the flood tables and the depth history through its own read-only roles.
`flood-routing-frontend` loads tiles from MinIO through nginx and sends requests to `floodmap-backend`.

### Block diagram

[[architecture-block-diagram]]

## 4. Core components

### 4.1 Simulation pipeline (Built)

Four Airflow DAGs run the pipeline.
`flood_mapping_full` runs the cycle.
It has the schedule `*/15 * * * *`, `catchup=False`, and `max_active_runs=2`, so a run that takes longer than 15 minutes overlaps the next slot.
The other three DAGs run on Airflow assets that the previous DAG emits, so a failure in one of them leaves the core run green.
`flood_tiles` runs on `flood_depth_files` (section 4.2), `routing_adapter` runs on `flood_depth_raster_tile` (section 4.11), and `flood_history` runs on `edge_depth` (section 4.5 and ADR-019).
Three Airflow pools limit concurrency: `threedi_trigger` (2 slots), `depth_calc` (1), and `routing_adapter` (1).
An operator creates them once by hand (README, "Create the Airflow pools").

`flood_mapping_full` has 9 tasks:

```
0_check_forecast_rain --(dry, and no flood stands)--> run ends successfully, every later task skipped
        |
      (rain, or a flood stands)
        v
1_trigger_simulation --> 2_download_results --> 3_calculate_depth --> 3b_publish_depth_files (emits flood_depth_files)
        |                        |                      |
        |                        v                      +--> 9b_load_depth_raster (emits flood_depth_raster_tile)
        |               2b_archive_results --> 2c_archive_done --> 3b
        v
0b_ensure_schema --> 3b, 9b
```

- **Rain gate.** `0_check_forecast_rain` reads the Tomorrow.io forecast for the next 2 hours
  (`FLOOD_RAIN_LOOKAHEAD_HOURS`).
  The run continues when an interval reaches `FLOOD_RAIN_THRESHOLD_MM_HR` (default 5 mm/h).
  A forecast with no intervals raises an error, because an empty answer is not a dry cycle.
- **Standing flood.** The threshold only starts a simulation from a dry state.
  When the forecast is below it, the gate reads the newest runs of `edge_depth` (`scripts/standing_flood.py`).
  The simulation stays on until the newest 5 runs are all under 5 cm (`FLOOD_DRY_DEPTH_M`) and no rain is forecast.
  A chain breaks when two runs are more than 30 minutes apart or the newest run is older than 45 minutes.
  A dry cycle with no standing flood ends as a success.
  A flood outlasts the rain, and in the replay of 2026-10-10 the gate alone would have skipped 4 of the 46 slots of the event window (`BL-028`, `US-101`).
- **Forecast mode.** Each gate decision writes one row to `forecast_mode`: `LIVE`, `PENDING`, or `DEMO` (`scripts/forecast_mode.py`, ADR-015).
  Task `9b_load_depth_raster` moves the row of its slot from `PENDING` to `LIVE`.
  A failed write is printed and does not stop the gate.
- **Stale-run guard.** Five tasks (`0`, `1`, `3`, `3b`, `9b`) skip when the slot of the run is older than `FLOOD_STALE_RUN_MINUTES` (default 120, `0` turns it off).
  An unpause or a long queue revives runs of past slots, and without the guard they would start real 3Di simulations (`US-139`).
  On 2026-10-13 the unpause of the DAG resumed a run left from 2026-10-10 before the guard existed, and two real simulations started with 0 mm/h forecast.
  The guard skipped three tasks with a date 7 hours old under real Airflow on the server later that day (log of 2026-10-13).
- **Run shape.** Each run starts at its 15-minute clock slot and simulates `SIMULATION_DURATION` seconds (default 7200).
  The output interval is 900 s and skips output step 0.
  The result is 8 depth steps per run.
  No code in the repository sets the output interval, and `UPDATE_INTERVAL` is read nowhere, so the interval comes from the 3Di template (unverified).
- **Archive.** Task `2b_archive_results` copies `results_3di.nc` and a `run_record.json` (simulation id, rain input, model id, graph hash, slot) to the archive folder, only when the rain source is real (`scripts/archive_results.py`, ADR-020).
  It fails when the free space of the drive falls under `ARCHIVE_MIN_FREE_GB` (default 50).
  `2c_archive_done` runs when `2b` ends, failed or not, so a full archive drive does not stop `3b_publish_depth_files`.
- **Hotstart.** Each run saves timed states at the cycle length. The next run hotstarts from the saved
  state whose `valid_at` equals its slot, or from the newest state up to two cycles older. With none, it
  cold starts. `hotstart_policy.should_hotstart` forces a cold start when the previous slot has no
  successful or running run (`FLOOD_COLD_START_AFTER_BREAK`, on by default). The reason is that stopping
  an Airflow run does not stop its 3Di simulation, so an old saved state can carry a storm that kept
  growing.
- **3Di sequence.** Connect with the personal API token, create the simulation from the template, upload
  the rain time series, attach the saved state, start, poll with a bounded backoff, and download the first
  `.nc` file. `gridadmin.h5` and `dem.tif` are static inputs under `data/mapping/inputs/`. Full detail is in
  [[3di-simulation-orchestration]].

Original design: two cycles. `constant_cycle` simulated 6 hours at a 15-minute timestep (25 GeoTIFFs per
run), started back to back, and was budgeted at 30 minutes. It hot-started from gauge water levels in
`initial_waterlevels.csv` and uploaded a `rain.nc` file. `background_cycle` simulated 24 hours at a
60-minute timestep on a 3-hour schedule. The built cycle is shorter (2 hours, 8 steps), starts from a
saved state, and uploads a time series. `background_cycle` is Dropped (ADR-005).

One-time manual setup, outside the pipeline and updated only on model rebuild: the 3Di model (versioned
geopackage from 1 to 2 m LiDAR DTM, building footprints, drainage network, Manning's n), the
calculation-node mapping, and the simulation templates. Original design: a fixed rainfall spatial
mapping from NCHMF grid cells to mesh cells. That mapping belongs to the unbuilt NCHMF input.

### 4.2 Depth calculation and its independent consumers (Built)

`scripts/calculate_depth.py` runs `threedidepth` per timestep and writes 8 `depth_YYYYMMDD_HHMMSS.tif`
files per run (filenames in Vietnam local time, UTC+7).
Original design: 25 files per cycle.
Tasks and DAGs read the depth files, the results, or the output of an earlier consumer.
Routing and map display run on different pipelines and cadences by design.
This is not an incomplete migration.
See [[minio-flood-extent-pipeline]].

| Consumer | Reads | Writes | Serves |
| --- | --- | --- | --- |
| `9_build_flood_tiles` in the DAG `flood_tiles` (`flood_extent.py`, GRASS GIS, via `publish.py`) | Depth files of the run that the event of `flood_depth_files` names, first `FLOOD_EXTENT_TILE_STEPS` steps (default 2) | `flood_extent_polygon`, `flood_extent_step`, MinIO `flood-extent/runs/<run_ts>/<timestep>/{z}/{x}/{y}.pbf` | Map overlay (`GET /flood/runs`, `GET /flood/timesteps`) |
| `9b_load_depth_raster` (`raster_load.py`) | Depth files, all 8 steps | `flood_depth_raster_tile` (EPSG:4326, 256 by 256 pixel tiles) | `GET /flood/points`, `POST /flood/forecast`, `POST /flood/profile`, and the input of `routing_adapter` |
| `routing_adapter` task `9c_build_edge_depth_table` | `flood_depth_raster_tile`, `graph_edge` | `<run_ts>.bin` in the volume `edge-depth-tables`, `edge_depth`, `edge_depth_run` | Time-aware engine, `POST /route/departures`, map overlay (`GET /flood/areas`), route fallback, rain gate, soak checks, flood metrics |
| `flood_history` task `load_depth_history` (`load_run.py`) | `edge_depth`, `edge_depth_run` | TimescaleDB `depth_history`, `history_moment` | The `analysis` container (section 4.14) |
| `2b_archive_results` (`archive_results.py`) | The downloaded `.nc` file | `results_3di.nc` and `run_record.json` in the archive folder | Analysis after a storm, and the rebuild of a run (ADR-020) |

The task `3b_publish_depth_files` writes nothing.
It emits the asset event `flood_depth_files` with `run_ts` and `depth_dir`, after `3_calculate_depth` and `2c_archive_done`.
The DAG `flood_tiles` owns the age-based cleanup of the result and depth folders (`FLOOD_EXTENT_CLEANUP_MAX_AGE_HOURS`, default 24), so a later consumer of the depth files must not delete them (ADR-018).
The tile build reads only the depth files.
The `postgis` input that read `flood_depth_raster_tile` was deleted on 2026-10-13 (`US-140`, `BL-029`).

Original design: the road-depth chain read the depth files itself (`extract_geojson.py` and
`scripts/mapping/*`, then `geojson_to_pg.py`, then `flood_road_values`). The raster-first pipeline
replaced it, and the routing tasks read the stored raster tiles (ADR-003).
That pipeline kept a second sampler, `flood_on_roads`, beside the edge depth build.
ADR-014 merged the two, and `flood_on_roads` was deleted on 2026-10-13.

### 4.3 Filename-to-UTC conversion (Built)

`calculate_depth.py` writes filenames in Vietnam local time (UTC+7). `publish.valid_time_utc()` converts
that to UTC before it writes `valid_time_utc` in `flood_extent_polygon`, `flood_extent_step`, and
`flood_depth_raster_tile`. `flood_extent_runs.list_timesteps` converts back to local time for `GET
/flood/timesteps`, because MinIO's folder names stay keyed by the local-time string. A wrong conversion in
either direction makes the endpoint return a time that matches no tile, off by exactly 7 hours.
`edge_depth.valid_time_utc` and `edge_depth_run.valid_times` follow the same rule, in UTC without an offset.
The exception that stored UTC+7 in `flood_road_values` is gone with that table.
`extract_run.py` converts the UTC step times back to Vietnam local time for the metrics (`VIETNAM_UTC_OFFSET`).
See [[core-output-contract]], "Time convention".

### 4.4 Postprocessing workers from the original design

The original whiteboard design specifies a metric extractor and four Tier 1 and two Tier 2 workers.

- **Flood metric extractor (Built, not scheduled).** `scripts/flood_metrics/metrics.py` and
  `extract_run.py` compute time-to-peak, recession onset, per-vehicle restoration time, and a pre-closure
  time per edge and vehicle, plus the forecast depth at T+1h and T+2h (`forecast_depth_1h_m`, `forecast_depth_2h_m`).
  `extract_run.py RUN_TS` reads `edge_depth`, `edge_depth_run`, and `graph_edge`, and writes `flood_segment_metrics` in `storage-postgres`, keyed by `edge_key` (`US-121`, ADR-014).
  No DAG task calls it, and the DAG does not create that table.
  An operator created it on the server on 2026-10-13 (log of 2026-10-13).
  See [[flood-metric-extractor]].
- **Tier 1 tile generator (Built).** It is `9_build_flood_tiles` (ADR-001).
- **Tier 1 segment extractor (Built, in a different shape).** It is task `9c_build_edge_depth_table` in `routing_adapter`, which writes the wet edges to `edge_depth`.
  It has no alert machinery around it.
  Retired: the first form, the task `flood_on_roads` and the table `flood_road_values` (ADR-003), ran from 2026-09-25 until ADR-014 deleted it on 2026-10-13.
- **Tier 1 institution histogram builder (Dropped).** ADR-005.
- **Tier 1 user alert engine, Tier 2 segment alert engine, Tier 2 district aggregator (Designed, not built).**
- **Edge depth table builder (Built, not in the original design).** Task `9c_build_edge_depth_table`
  (section 4.11).
- **Depth history loader (Built, in a different shape).** The DAG `flood_history` copies each run from `edge_depth` into `depth_history` and `history_moment` in TimescaleDB, one row per edge and moment, and keeps them for one year (ADR-019).
  Original design: TimescaleDB held the depth history, filled by the postprocessing workers.

### 4.5 Flood Routing Engine (Built, on GraphHopper with a time-aware module)

The original design marked this component a black box on the whiteboard and named Valhalla as the
implementation. The built system replaced Valhalla with GraphHopper (ADR-002) and added a time-aware
search (ADR-008). Full detail is in [[graphhopper-backend]].

- **Image.** `graphhopper` builds from `java/time-aware-routing/Dockerfile`. That file takes the stock
  image `israelhikingmap/graphhopper@sha256:3e79eb33862028cfc58f9d6c162630b68638d6aad790b5a698c854dbbaa7fe32`
  (a 12.0-SNAPSHOT build) as its base by digest, and puts the module's jar first on the classpath. The
  `ch.disable`-in-body behavior that flood-graded routing depends on is undocumented, so the digest stays
  pinned. `compose.yml` keeps the stock image line as a comment for rollback.
- **Grade by `custom_model`.** `floodmap-backend` derives a `custom_model` from PostGIS through `flood_areas.derive_areas` and forwards the graded request.
  The function reads the wet edges of `edge_depth` and takes their geometry from `graph_edge`.
  The run that wins a forecast time is the newest run in `edge_depth_run` whose `valid_times` contains the time, so a run with no wet edge still wins.
  `GET /flood/areas` and `POST /route` call the same function, so the overlay and the routing cannot drift apart.
  The engine reads the file that task `9c` writes in the same pass, so the map, the fallback, and the engine see the same water (ADR-014).
  The edge geometries of a band are buffered by 22 m and merged, the parts are simplified by 3 m, and a part under 400 m2 is dropped.
  A wet edge is drawn whole, so on 2026-10-12 the new overlay covered about 2.2 times the area of the old one (log of 2026-10-12).
  `flood_utils.DEPTH_BANDS` grades each edge in bands of 0.5, 0.75, and 1.0 times the vehicle's limit.
  The top band (`b4`) is impassable.
  See [[routing-depth-threshold-model]].
- **Time-aware search.** With `TIME_AWARE_ROUTING` on, `POST /route` sends a departure to the engine.
  The engine runs `TimeAwareDijkstra` over the edge depth table, applies the sticky closure rule (D-023), and falls back to the `custom_model` request when the table is missing, stale, or for another graph.
  The response carries `td.status`.
  An applied answer can carry two paths (D-021).
  Path 0 is the recommended route that avoids roads at the precaution depth, 50 percent of the vehicle's limit (`DEFAULT_PRECAUTION_FRACTION` in `TimeAwareRouter.java`), and path 1 is the route at the hard limit.
  The hints `td.kinds`, `td.limit_cm`, and `td.precaution_cm` come with them.
  The flag defaults to `false` in `compose.yml` and `.env.example`.
  The server `.env` sets it to `true` since 2026-10-12, by the owner's decision (D-034), and a read-back that day printed `true` in the container `airflow_new-floodmap-backend-1`.
  The engine was deployed and tested on the server on 2026-10-07 (compare, crossings, departures, latency within 2x, and scenario-check 32/32 passed).
  `scripts/routing_proof/rollout.ps1` turns the flag on for a proof and puts it back off unless run with `-LeaveOn`.
  In `DEMO` mode the route skips the engine and reads the pinned step through the flood areas (ADR-015).
  The limit of `US-045` was met: on 2026-10-13 a run took 148 s from `3_calculate_depth` to the end of `9c`, against 5 minutes (log of 2026-10-13).
  The soak `roads` check tests that a blocked edge blocks the route (section 4.13).
- **Vehicle limits.** `flood_utils.py` `VEHICLE_PROFILES` is the one owner: motorbike 20 cm, car 30 cm, truck
  35 cm, foot 40 cm. `config.yml` repeats them as `td_limit_cm`, and a test keeps the two equal. All four
  profiles are live.
- **Pre-closure.** Original design: pre-closure segments cost infinity. The built grading has no
  pre-closure term. The metric extractor computes a pre-closure time, and routing does not read it. The
  time-aware engine uses a 600 s margin (`MARGIN_S` in `departures.py`) in its closure rule.
- **Valhalla.** `floodmap/valhalla-flood-road-test/` was deleted in commit `5d1a606` (2026-09-23).
  Original text said it stayed on disk.

### 4.6 REST API and backend (Built subset and Designed subset)

**Built**, served by `floodmap-backend`:

| Path | Method | Purpose |
| --- | --- | --- |
| `/health` | GET | Backend, GraphHopper, and PostGIS health in one payload |
| `/info`, `/nearest` | GET | Proxied to GraphHopper unchanged |
| `/flood/runs` | GET | Distinct `run_ts` values from `flood_extent_polygon` |
| `/flood/timesteps` | GET | Timesteps for one run, converted to Vietnam local time |
| `/flood/mode` | GET | The map mode `LIVE`, `PENDING`, or `DEMO`, when it was decided, and the pinned demo step (ADR-015) |
| `/flood/areas` | GET | The flood polygons that `POST /route` grades against, for the map overlay, from `edge_depth` and `graph_edge`. In `DEMO` mode it reads the pinned step. |
| `/flood/points` | GET | Depth at one latitude, longitude, and time, from `flood_depth_raster_tile`. In `DEMO` mode it reads the pinned step. |
| `/flood/forecast` | POST | Mean depth along a route at 15-minute steps, from `flood_depth_raster_tile` |
| `/flood/profile` | POST | Depth at samples along a route at one timestep |
| `/route` | POST | Flood-graded route, or time-aware route with the flag on (section 4.5). In `DEMO` mode it reads the pinned step through the flood areas and skips the engine. |
| `/route/departures` | POST | Earliest clear departure of the usual route (`US-053`) |
| `/places/search`, `/places/reverse`, `/geocode` | GET | Place search and geocoding through Photon. The public instance is slow, and `/places/reverse` answers 504 when Photon takes more than 5 s (`BL-021`). |

The backend connects as the read-only role `routing_reader`, waits up to `FLOOD_DB_POOL_WAIT` seconds
(default 5) for a pooled connection, and answers 503 with `Retry-After` when none frees up.
The frontend does not read `GET /flood/mode` yet, so the banner of the `DEMO` mode is not built (`US-131`).

**Designed, not built** (the original citizen REST API sketch): `GET /flood/tiles/{z}/{x}/{y}`
(superseded by `/flood/runs`, `/flood/timesteps`, and the MinIO `.pbf` path, so not a gap, see ADR-001),
`POST /community/report`, `POST /user/location`, `GET /flood/alerts`, `GET /places/flood`, and the council
dashboard set (`/dashboard/preclosure`, `/dashboard/institutions/access`, `/dashboard/dispatch`,
`/dashboard/districts/summary`). Original design: `GET /flood/points` and `GET /flood/route/forecast` were
also in this list. They are built, as `GET /flood/points` and `POST /flood/forecast`.

### 4.7 Mobile and web app (Designed, not built, with a built web slice)

No mobile app exists. The original design specifies a map view with layer toggles and vehicle-mode
selection, a route planner with per-step depth badges and a route flood-depth histogram, a flood status
bottom sheet, an institution place-detail sheet with a 24-hour "popular times" histogram, an alert manager
(an FCM or APNs receiver and an in-app `/flood/alerts` poller as the delivery-guaranteed channel), and a
community reporter (photo, depth estimate, passability vote, isolated from routing, pins expire after 2
hours unless reconfirmed).

The built client is `flood-routing-frontend` (`floodmap/graphhopper-maps`, source in `src/floodmap/`). It
has these parts:

- A map mode toggle and a flood legend with an "As of" or "Forecast for" time line (`FloodLegend.tsx`,
  `timestepLabel.ts`, D-010).
- The `.pbf` flood overlay from MinIO (`FloodExtentLayer.tsx`).
- Four vehicle profiles: motorbike, car, truck, and foot.
- Per-step depth in the route instructions and depth badges along the route (`RouteDepthBadges.tsx`).
- A place depth popup on map tap (`PlaceDepthPopup.tsx`).
- A depth-over-time chart for a route (`DepthForecastChart.tsx`).
- "Wait until" advice in the no-route alert (`departureAdvice.ts`, `US-054`).

The app opens in Flood mode (D-008). Alerts, the community reporter, and the institution sheet are Designed,
not built.
The mockup recheck (`US-076` to `US-085`) and the demo banner (`US-131`) belong to the epic `EP-19`.
None of them has started, because Sprint 14 holds backend stories only (D-041).

### 4.8 City council dashboard (Designed, not built)

No dashboard exists in this repository. The original design specifies four layers. Situational awareness
covers a full-city flood heatmap, a staleness banner, and district summary counts. A pre-closure alert feed is
the primary dispatch trigger, with an institution access panel. A dispatch workflow layer has an action panel
with duplicate-dispatch prevention, a chronological deployment log exportable as CSV, and an announcement
composer that drafts Vietnamese text for manual publishing. A forecast and planning layer has a 24-hour
district forecast with a timestep scrubber, a peak-and-recession timeline, and a pipeline health monitor
that reads `GET /pipeline/status`, which also does not exist.

### 4.9 Histogram specifications

- **Institution histogram (Dropped).** The design specified 24 hourly bars: bars 1 to 6 from `constant_cycle`
  and bars 7 to 24 from `background_cycle`. D-009 dropped `background_cycle`, so the 24-bar histogram cannot
  be built as specified (ADR-005).
  The tables `institution_histogram_bar` and `background_forecast_depth` exist in TimescaleDB and stay empty.
  `depth_history` is filled since 2026-10-12 by `flood_history` (ADR-019), but it holds one value per edge and moment for the industry applications, not the 24 bars.
- **Route histogram (Built, in a different shape).** `POST /flood/forecast` computes it at query time from
  `flood_depth_raster_tile`, as the original design required, and not from a pipeline worker. The window is
  8 steps of 15 minutes (2 hours), starting at the step that contains `from`. Original design: 8 bars at
  30-minute resolution over 4 hours, computed from PostGIS per-segment forecast depths, served by `GET
  /flood/route/forecast`. The built version reads raster tiles because `edge_depth` covers road edges only, and matching a route to its rows has no stable key (docstring of `flood_forecast.py`).

### 4.10 Core output contract (Built)

The pipeline publishes results that other applications read. [[core-output-contract]] lists them and
`floodmap/graphhopper-flood-road/backend/test_core_contract.py` compares its column tables with the live
database.
The contract names nine PostgreSQL tables, the edge depth files, and the vector tiles.
Routing is the first consumer, and the `analysis` container is the second (section 4.14).

| Output | Writer | Kept |
| --- | --- | --- |
| `flood_depth_raster_tile` | `9b_load_depth_raster` | Newest 8 runs (`FLOOD_RASTER_KEEP_RUNS`) |
| `flood_extent_polygon` | `9_build_flood_tiles` | Newest 8 runs (`FLOOD_EXTENT_KEEP_RUNS`) |
| `flood_extent_step` | `9_build_flood_tiles` | Newest 8 runs |
| `flood_run_output` | `9b_load_depth_raster`, `9_build_flood_tiles`, `9c_build_edge_depth_table` | Newest 8 runs |
| `edge_depth`, `edge_depth_run` | `9c_build_edge_depth_table` | The 24 hours before the newest run (`EDGE_DEPTH_KEEP_HOURS`) |
| `forecast_mode` | `0_check_forecast_rain`, `9b_load_depth_raster` | The last 7 days |
| `demo_pin` | `scripts/database/demo_pin.py`, run by an operator | One row, until replaced |
| `graph_edge` | `9c_build_edge_depth_table` | The loaded graph |
| Edge depth files | `9c_build_edge_depth_table` | Newest 8 runs (`EDGE_TABLE_KEEP_RUNS`, D-033) |
| Tiles in `flood-extent` | `9_build_flood_tiles` | Newest 8 runs |

Every prune keeps the pinned demo run (`demo_pin.kept_runs`): the tables, the MinIO prefix, and the edge depth file (ADR-015).
The prune of `edge_depth` keeps its rows for 24 hours before the newest run.
Before 2026-10-13, `flood_road_values` and `flood_road_file` were contract tables, pruned after 24 hours (D-017).
ADR-014 deleted them.

`flood_run_output` is the run manifest (`US-108`).
One row says that one output of one run is published, and `output` is one of three values: `depth_raster`, `extent`, or `edge_depth`.
A consumer outside Airflow reads the manifest instead of polling three places.
`flood_extent_step` says that a step is fully published.
The asset `flood_depth_raster_tile` (`dags/core_assets.py`) says that every step of a run is in `flood_depth_raster_tile`, and its event carries `{"run_ts": "<run_ts>"}`.
ADR-010 explains why `routing_adapter` runs on it.
The asset `edge_depth` says that the rows of a run are in `edge_depth` and `edge_depth_run`, and `flood_history` runs on it.
Each consumer connects as its own read-only role.
`routing_reader` can read 9 tables and `analysis_reader` can read 4 (`flood_extent_step`, `flood_extent_polygon`, `flood_depth_raster_tile`, and `flood_run_output`).
The lists live in the contract page, and `scripts/database/create_routing_reader_role.py ROLE` reads them with `core_contract.parse_reader_roles` (ADR-011).
The worker mounts the parser and the contract page read-only, so the script runs in the worker (`US-132`).

### 4.11 Edge depth table (Built)

One file holds the flood depth of every GraphHopper edge at every forecast step of one run. The file
`<run_ts>.bin` is edge-major, with a header (`EDGD`, version, step count, edge count, graph hash, run name,
step times) and one 16-bit centimetre depth per edge and step. The real graph has 67,833 edges, so a file
with 8 steps is 1,085,487 bytes. A `latest` text file names the current table. The task writes under a
temporary name and renames, moves `latest` only forward, and keeps the newest 8 files (D-033) and the file of the pinned demo run.
Both readers refuse a table whose graph hash differs from the loaded graph's.
The byte layout is in [[edge-depth-table-format]].
After a graph re-import, follow [[graph-reimport-procedure]].

The same pass of task `9c_build_edge_depth_table` writes the wet edges to the table `edge_depth` and one registry row to `edge_depth_run`.
It does this in one transaction before it writes the file, so a database failure leaves no file and no new `latest`.
The registry row lists every forecast time of the run, so a run with no wet edge still counts (ADR-014).
`edge_depth` is keyed by `edge_key`, `<osm_way_id>:<position along the way>`, which `graph_edge` carries and which survives a re-import of the same OSM file.
`GET /flood/areas`, the route fallback, the rain gate, the standing-flood rule, the soak checks, the flood metrics, and the depth history all read `edge_depth`.
Task `9c` then emits the asset `edge_depth`, which starts `flood_history`.

Task `9c_build_edge_depth_table` reads the graph export (`graph.json` and `edges.csv`, format 3) that `java/time-aware-routing/export-edges.sh` writes.
Airflow cannot run the export because it needs the GraphHopper image.
The export carries `edge_key` since 2026-10-12, after a re-import of the live graph with `osm_way_id` (`US-117`).
Measured on the server on 2026-10-13: task `9c` took 24.2 s and 24 s on two real runs, 79.5 s at most (69.9 s on average) over 50 consecutive runs of the test dataset with the row writes included, against a limit of 150 s (`US-118`), and a run took 148 s from `3_calculate_depth` to the end of `9c`.
The 50-run figure is an upper bound for production, because the test database kept every run and production keeps 24 hours.
The answers of `GET /flood/areas`, `GET /flood/points`, and `POST /route` did not change when the old tables were dropped (log of 2026-10-13).

### 4.12 Rain replay tooling (Built)

A replay feeds a recorded rain event to the DAG instead of Tomorrow.io, so the pipeline can run under rain
on a dry day. `FLOOD_TEST_RAIN_CSV` and `FLOOD_TEST_RAIN_START` select the event. `scripts/rain_replay.py` has
the subcommands `preview`, `next-slot`, `check`, and `status`. `scripts/rain_env/replay.ps1` has `start`,
`stop`, and `status`. It saves the prior `.env` values, recreates only `airflow-worker`, reads the setting
back from inside the worker, and does not unpause the DAG. The event files are
`scripts/rain_events/hanoi_20251005_48h.csv` (48 hours) and `hanoi_20260916_storm.csv` (12 hours, 53.88 mm,
peak 8.73 mm/h).
The folder also holds `constant_5mm_2h.csv`.
`replay.ps1 start` ran on the server on 2026-10-08, and `stop` ran at 18:49 +07 on 2026-10-10 and read back `mode live` (`US-089`, log of 2026-10-10, ADR-012).
The replay of 2026-10-10 ran from 04:45 to about 18:15 +07 with every run `success`, and the 58 runs of that storm are kept as the test dataset (section 9, ADR-017).

### 4.13 Verification tooling (Built)

| Tool | Checks |
| --- | --- |
| `scripts/backend_soak/run_soak.sh`, `soak_checks.py` | The 48-hour soak of the backend (`US-034`) and the `roads` check, described after this table |
| `scripts/routing_reference/` | A slow, readable implementation of sticky closure, used as the reference for the Java engine ([[sticky-routing-reference]]) |
| `scripts/routing_proof/rollout.ps1`, `routing_proof.py` | The server proof of the routing engine (`US-055`) |
| `scripts/edge_depth/table_timing.ps1`, `spot_check.py`, `check_tables.py` | Build time, `ST_Value` spot check, and hash agreement of the edge depth table |
| `scripts/pipeline_margins/` | The step-1 margin of every run |
| `scripts/storage_check/read_storage.ps1` | Disk and database sizes |
| `scripts/testdata/run_db_tests.py` | The database suites of the repository, run against scratch databases (section 9, ADR-017) |
| `scripts/testdata/restore_snapshot.py`, `rebuild_tiles.py`, `build_history_and_metrics.py` | Fill the test databases from the stored storm, and rebuild the raster tiles of a stored run from its NetCDF (`US-126`, D-046) |

The `roads` subcommand of `soak_checks.py` picks real edges from `edge_depth` whose depth lies between two vehicle limits.
For each vehicle it sends the dry control request straight to GraphHopper, because the backend floods even a request with no run and `valid_time`.
It then sends `POST /route` to the backend and compares the answer with the answer that the limits give.
Under `TIME_AWARE_ROUTING` the engine judges the cell named in the hints `td.run` and `td.departure`, so the check reads that cell first (`US-120`, `US-133`).
It fails when it judged no blocked pair, and it skips a pair whose dry route runs on other blocked roads (`US-138`).
The choice of pairs explained three false failures on 2026-10-13, and the routing was correct (D-050).
On the server the check gave 0 failures with 7 blocked pairs judged (log of 2026-10-13).
The comparison of `LIVE` and `DEMO` routes uses only points that are dry and at least 150 m from the flood (D-044).

### 4.14 Analysis service (Built, with no analysis application yet)

The container `analysis` is the home of the industry analysis applications of the epic `EP-21` (`US-109`).
It has its own image and requirements file, so an analysis developer adds libraries and tables without touching the Airflow image or the pipeline tables.
Its only endpoint is `GET /health`.
The endpoint returns the newest `run_ts` whose outputs in `flood_run_output` are exactly `depth_raster`, `extent`, and `edge_depth`, or null when no run has all three.
It answers 503 when the database refuses the connection.
The service has three credentials and no other secret.
The service in `compose.yml` has no `env_file`, so the 3Di, Tomorrow.io, and MinIO keys never reach it, and `test/test_analysis_service_compose.py` fails when one is added.

| Role | Database | Rights |
| --- | --- | --- |
| `analysis_reader` | `storage-postgres` | `SELECT` on `flood_extent_step`, `flood_extent_polygon`, `flood_depth_raster_tile`, and `flood_run_output` |
| `analysis_owner` | `storage-postgres` | Owns the schema `analysis`, the only place the service writes, and has no right on schema `public` |
| `analysis_timescale_reader` | `timescaledb` | `SELECT` on `depth_history` and `history_moment` |

The service does not use the owner and TimescaleDB credentials yet.
Detail is in [[analysis-service]].

## 5. Data stores

| Store | Type | Status | Holds |
| --- | --- | --- | --- |
| `storage-postgres` | PostgreSQL 17 and PostGIS 3.5 | Built | The 11 pipeline tables in schema `public` (ADR-016): `edge_depth`, `edge_depth_run`, `flood_depth_raster_tile`, `flood_extent_polygon`, `flood_extent_step`, `flood_run_output`, `forecast_mode`, `demo_pin`, `graph_edge`, `graph_edge_export`, and `flood_segment_metrics`. Also `minio_custom`'s role and access-group tables (14 Django tables) and the schema `analysis`. The tables `flood_road_values`, `flood_road_file`, `road_segment`, and `flood_road_values_shadow` are Retired and were dropped on 2026-10-13 (ADR-014). |
| `timescaledb` | TimescaleDB 2.30.1 | Built | `depth_history` (one row per edge and moment, 7-day chunks, compressed per closed chunk, dropped after 365 days) and `history_moment` (one row per moment a run covered, dropped after 365 days), both written by `flood_history` (ADR-019). The tables `institution_histogram_bar` and `background_forecast_depth` exist and stay empty. The tables `netcdf_values`, `mesh_elements`, and `netcdf_variable_catalog` are Retired and were dropped on 2026-10-10 (ADR-007). |
| MinIO | S3-compatible object store | Built | `initial-wl`, `manholes-data` (private), `flood-extent` (public download, `.pbf` tiles). The bucket `flood-results-full` is Retired (ADR-004). |
| Volume `edge-depth-tables` | Docker named volume | Built | Edge depth files and the `latest` pointer |
| Archive folder | Bind mount `ARCHIVE_HOST_PATH` on the worker | Built | `<sim_id>/results_3di.nc` and `run_record.json` of each real-rain run (ADR-020) |
| Test dataset folder | Bind mount `data/testdata/storm-2026-10-10/` on the worker | Built | 58 `results_3di.nc` files, a snapshot of derived tables, and edge depth files (ADR-017). No retention. |
| Volume `graphhopper-graph-cache` | Docker named volume | Built | The imported GraphHopper graph |
| `airflow-postgres` | PostgreSQL 16 | Built | Airflow's metadata database |
| `airflow-redis` | Redis 7.2 | Built | Airflow's Celery broker. Not the multi-role Redis below. |
| Redis (task queue, pub-sub, short-TTL cache) | Redis | Designed, not built | Postprocessing fan-out, cycle-completion events, API response cache |
| User Location Store | PostgreSQL | Designed, not built | User GPS and consent mode, read by the user alert engine, which is also unbuilt |
| PostGIS extended schema (dispatch log, community reports, district summary, institutions) | PostgreSQL and PostGIS | Designed, not built | None of these tables exist |
| `flood_segment_metrics` | PostgreSQL table in `storage-postgres` | Built, not scheduled | Output of `extract_run.py`, keyed by `edge_key`. An operator created it on 2026-10-13, and `0b_ensure_schema` does not create it. |
| `minio_custom_test`, `flood_metrics_test` | Databases on `storage-postgres` and `timescaledb` | Built | The restored test dataset (ADR-017). No pipeline reads them. |

TimescaleDB runs in its own database, `flood_metrics`, with its own credentials (`TIMESCALE_*`).
Original design: TimescaleDB held institution histograms, `background_cycle` forecast series, and depth
history.
It holds the depth history only, in a different shape (ADR-019).
The histograms and the forecast series stay empty.

## 6. External integrations

| Service | Purpose | Integration | Status |
| --- | --- | --- | --- |
| 3Di (`api.3di.live`) | Hydraulic simulation | REST API, personal API token | Built |
| Tomorrow.io | Rain forecast | HTTPS, `GET /v4/timelines`, once per cycle | Built |
| NCHMF | Rainfall forecast (GRIB2 or NetCDF) | HTTPS poll | Designed, not built (section 2) |
| Gauge network APIs | Observed water levels for hot start | HTTPS, cycle start | Designed, not built. A scrape of `thoatnuochanoi.vn` exists in `manholes_dag.py` and feeds nothing in the cycle. |
| Photon (`photon.komoot.io`) | Place search, reverse geocoding | HTTPS, 5 s timeout | Built, slow. The public instance answered in 4 to 6.5 s on 2026-10-13 and 11 of 12 reverse calls timed out. A Photon instance for Vietnam next to the backend is `US-141`, on hold ([[BL-021-place-name-slow-after-map-tap\|BL-021]], P3). |
| FCM and APNs | Push alerts | HTTPS or FCM REST | Designed, not built |
| Google Maps | Place search and geocoding for the citizen app | n/a | Designed, not built. Photon fills the role in the web client. |
| GitHub Actions | CI for the Java module (`java-module.yml`), the flood area tests against a PostGIS service (`flood-areas-test.yml`), and the restore script of the test dataset (`restore-snapshot-test.yml`) | GitHub | Built |
| Ride-hailing partner API (Phase 3) | Batch depth queries (`POST /partner/flood/points`), MVT serving (`GET /flood/vtiles/{z}/{x}/{y}.mvt`), B2B API keys with per-partner rate limits | n/a | Designed, not built. It would extend the built vector-tile pipeline (section 4.2), not the retired raster one the original sketch assumed. |

## 7. Deployment and infrastructure

- **All Docker workloads run on one remote Windows host**, never the local machine. The host is the
  machine `TECOTEC` at `100.67.84.55` (the shell prompt calls it `ADMIN`). The Compose project is
  `airflow_new`, so containers have names like `airflow_new-graphhopper-1`. On a Mac, `docker context ls`
  shows a `remote-server` context (`ssh://tecotec@100.67.84.55`). On the host itself there is no such context,
  and Docker commands run locally.
- **Start, build, and recreate on the host.** Compose expands relative bind-mount paths on the client.
  Run `docker compose` with `up` or `build` on the host over SSH, with `--no-deps`. Use `--context
  remote-server` from the Mac only for read-only commands. The host's shell is PowerShell 5.1, so chain
  commands with `;`, not `&&` ([[L-010-recreate-remote-services-on-the-remote-host|recreate-remote-services-on-the-remote-host]]).
- **Code reaches the host by git.** Push the branch, then pull on the host. The host's remote for this
  repository is named `alice`, so the pull is `git pull --ff-only alice modular`. The bind-mounted services
  (`./dags`, `./scripts`, `./data`) see the change after the pull.
- **Build `graphhopper` on the host.** `docker compose build graphhopper` builds the time-aware image from
  `java/time-aware-routing`. The OSM extract `../grasshopper-routing/osm/hanoi-model-area.osm.pbf` sits outside
  this repository (unverified on the host). A change to a vehicle profile needs a graph re-import
  ([[graph-reimport-procedure]]).
- **One deploy for the engine and the routing contract.** D-011 (ADR-013) put Sprint 11's stories and the
  engine stories into one server rollout. `scripts/routing_proof/rollout.ps1` runs it. Create the role and
  `ROUTING_READER_PASSWORD` in `.env` before the rollout.
- **Rollout order of a batch with new tables or roles.** Pull the branch on the host.
  Run the DDL through a task of `0b_ensure_schema` or by hand, and run `create_routing_reader_role.py ROLE` in the worker for each reader role.
  Rebuild `floodmap-backend` and `analysis` from the desktop of the server, because `docker build` over SSH fails on the credential helper.
  The worker reads `.env` only when it is created, so a new variable needs `docker compose up -d --no-deps airflow-worker`.
  `compose.yml` requires every role password with `:?`, so every `docker compose` command fails until `.env` holds them all.
  On 2026-10-13 the worker did not mount the parser and the contract page, so the role script failed there until `US-132` added the mounts.
- **Storage.** Docker's disk image `docker_data.vhdx` lives on the host's C: drive and has filled it
  ([[BL-022-docker-data-vhdx-fills-c-drive-again|docker-data-vhdx-fills-c-drive-again]]).
  `DATA_HOST_PATH` and `AIRFLOW_LOGS_HOST_PATH` point task data and logs at the D: drive, and `ARCHIVE_HOST_PATH` points the results archive at `D:\airflow_new_data\archive`.
  The edge depth tables use a Docker named volume on purpose (ADR-009).
  The drop of the four old road tables freed 377.1 MB on 2026-10-13 (log of 2026-10-13).
- **Two stacks share one database server.** `storage-backend` and `storage-frontend` form one stack.
  `graphhopper`, `floodmap-backend`, and `flood-routing-frontend` form another. Both use the single
  `storage-postgres` instance (default database `minio_custom`).
- **Map tiles.** The original design's S3 and CloudFront CDN does not exist. MinIO behind nginx serves tiles
  (ADR-001). `nginx.conf` in `graphhopper-maps` proxies `/flood-extent/` to the MinIO bucket and `/api/gh/`
  to `floodmap-backend:8010`.
- **Same host or not.** Comments in `compose.yml` say the Airflow worker and the frontend run on separate hosts in
  production. The deployment runs every service of this project on the one Windows host. Whether a second
  production host exists is unknown, and only the user can say. A container `be-responsiblebot-bot-1`, which
  does not belong to this project, also runs on the host.
- **Worker environment.** The values on the server matched the `compose.yml` defaults on 2026-10-08, and several changed after that date (see the next bullet):
  `FLOOD_TEST_RAIN_CSV=/opt/airflow/scripts/rain_events/hanoi_20260916_storm.csv`,
  `FLOOD_TEST_RAIN_START=2026-10-08T08:45:00Z`, `FLOOD_RAIN_THRESHOLD_MM_HR=5`, `FLOOD_RAIN_LOOKAHEAD_HOURS=2`,
  `FLOOD_RAIN_TIMESTEP_MINUTES=15`, `FLOOD_RAIN_CHECK_INTERVAL_SECONDS=900`, `FLOOD_COLD_START_AFTER_BREAK=1`,
  `FLOOD_EXTENT_TILE_STEPS=2`, `FLOOD_EXTENT_KEEP_RUNS=8`, `EDGE_TABLE_KEEP_RUNS=3`, `FLOOD_EXTENT_WORKERS=2`,
  `SIMULATION_DURATION=7200`, and `AIRFLOW_WORKER_CONCURRENCY=4`.
- **Changes recorded after 2026-10-08.** These come from the logs and were not read again on the server.
  `EDGE_TABLE_KEEP_RUNS` was 100 on the server during the replays and went to 8 on 2026-10-12 (D-033).
  `TIME_AWARE_ROUTING=true` is in the server `.env` since 2026-10-12 (D-034), and only `floodmap-backend` reads it.
  `ARCHIVE_HOST_PATH=D:/airflow_new_data/archive` was added on 2026-10-10 (D-016).
  The `compose.yml` defaults `ARCHIVE_MIN_FREE_GB=50`, `EDGE_DEPTH_KEEP_HOURS=24`, and `FLOOD_STALE_RUN_MINUTES=120` are new.
  `replay.ps1 stop` ran on 2026-10-10, so the `FLOOD_TEST_RAIN_*` variables are no longer set for the rain source.
  On 2026-10-13 the scheduler container read `FLOOD_RAIN_THRESHOLD_MM_HR=0.01` while the worker read 5.
  The scheduler, the worker, the API server, and the DAG processor were recreated that day, and all four read 5 (`US-134`).
  Every Airflow container must read the same gate value, so that the rain gate gives the same decision wherever it runs.
- **Retired-chain leftovers.** The worker also receives `SAMPLE_RATE` (`20` on the server on 2026-10-08), `UPDATE_INTERVAL=900`,
  `MIN_DEPTH_THRESHOLD`, `KEEP_LOCAL_GEOJSON`, `LOCAL_GEOJSON_DIR`, `FLOOD_USE_DOWNLOADED_RESULTS`,
  `FLOOD_LOCAL_FALLBACK`, and `VALHALLA_PORT`.
  A search with `git grep` on 2026-10-13 (excluding `artifacts/`, `marie-curie/`, and `digital-twin-artifacts/`) finds no code that reads any of them.
  Only `compose.yml` and `.env.example` mention the first six, and `VALHALLA_PORT` and `FLOOD_LOCAL_FALLBACK`
  appear nowhere in the repository, so the server's `.env` must set them. They belong to the retired Valhalla
  router and GeoJSON chain.
  The `compose.yml` default of `SAMPLE_RATE` is `1`.

## 8. Security considerations

- MinIO: only the `flood-extent` bucket allows anonymous download (`mc anonymous set download`). The MinIO API
  and console ports bind to `127.0.0.1`, so public access exists only through nginx's proxy.
- `storage-postgres`, `timescaledb`, and `analysis` publish their ports on `127.0.0.1` only (`compose.yml`).
- `graphhopper` (8989), `floodmap-backend` (8010), `flood-routing-frontend` (8082), `storage-backend` (8000),
  `storage-frontend` (5173), and the Airflow API server (8090) publish ports on all interfaces (checked on the
  server 2026-10-08). Windows Firewall is on for the domain, private, and public profiles. Nobody has read its
  rules, so which of these ports it allows from outside is unverified. `server.py` has no authentication code.
  Open item for the user to decide: the Airflow API server on 8090 is reachable on every interface.
- Open item for the user to decide: six DAGs are unpaused on the server, and three of them are manual or probe
  DAGs (`calculate_depth_manual_test`, `flood_forecast_consecutive_state_test`, `zz_cold_start_probe`). The
  first two have `schedule=None`. A person with access to the Airflow API server can trigger any unpaused DAG.
  The state of the other DAGs after 2026-10-08 is unverified.
  The stale-run guard (section 4.1) now skips the tasks of a run whose slot is older than 120 minutes, so an unpause no longer starts real 3Di simulations from old slots.
- `floodmap-backend` connects to PostGIS as `routing_reader`, a role limited to `SELECT` on its 9 contract tables
  with no `CREATE` on schema `public` (ADR-011). `docker compose` refuses to start the service without
  `ROUTING_READER_PASSWORD`.
  The role cannot write `forecast_mode` (checked on the server on 2026-10-13).
- The `analysis` container holds three credentials and no other secret.
  `analysis_reader` has `SELECT` on 4 contract tables, `analysis_owner` owns schema `analysis` and has no right on schema `public`, and `analysis_timescale_reader` has `SELECT` on `depth_history` and `history_moment`.
  The service has no `env_file`, so the 3Di, Tomorrow.io, and MinIO keys never reach it.
  The server check of 2026-10-12 showed each denial (a write to the old `flood_road_values`, a table in `public`, and a write to `depth_history`).
  The Airflow worker runs the role scripts and so holds the writer credentials for them.
- `minio_custom/backend` authenticates with JWT (`storage_api/authentication.py`) and has its own role, visibility,
  and access-group model, separate from the pipeline's bucket use. `compose.yml` defaults `DJANGO_DEBUG` to `true`.
  On the server `storage-backend` runs with `DJANGO_DEBUG=false` and
  `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,storage-backend,100.67.84.55` (checked 2026-10-08).
- The pinned stock GraphHopper digest is a stability control. The `ch.disable` behavior is undocumented in that
  build.
- GraphHopper logs the whole `custom_model` of each flood-graded `/route` request on one line, up to about
  450 KB, and the container log has no size limit ([[graphhopper-backend]], "Log volume").
- The original design's citizen-facing auth (community-report tokens, location consent tokens, council
  dispatch tokens) has no implementation. No citizen-facing authenticated endpoint exists.

## 9. Development and testing environment

- **Python tests.** `git ls-files '*test_*.py' | wc -l` printed 84 files on 2026-10-13 (51 on 2026-10-08).
  They sit in `test/` (DAG graphs, 3Di auth, MinIO bucket routing, NetCDF input, rain gate, state test, the analysis compose file, the reader role mounts), beside the code in `scripts/`, in `analysis-service/test/`, and in `floodmap/graphhopper-flood-road/backend/` (against a real PostGIS and a stub GraphHopper).
  Run them with `pytest` from the repository root or a test folder. The suite needs PostGIS and GDAL for the
  database and raster tests.
  `pytest.ini` puts the script folders on the Python path, and `test/conftest.py` gives a stand-in to the 3Di client names that an older client lacks (`US-137`).
  On 2026-10-13, `pytest test/` gave 129 passed and 1 skipped on the Mac, where it had 10 failures and 2 errors before `US-137` (log of 2026-10-13).
- **Database suites.** About 9 suites create and drop tables in `public` of their database, so they must never run against the test dataset or production.
  `python3 scripts/testdata/run_db_tests.py` opens an SSH tunnel to the server, creates one scratch database on `storage-postgres` and one on `timescaledb`, runs the suites, drops both, and fails when the row counts of the restored test tables change (`US-128`, ADR-017).
  On 2026-10-13 it gave 753 passed, 0 failed, 0 errors, and 8 skipped on the server, with the dataset unchanged (log of 2026-10-13).
- **Test dataset.** The 58 runs of the storm replay of 2026-10-10 are kept in `data/testdata/storm-2026-10-10/`.
  The `results_3di.nc` of each run is the source of truth, and the derived tables are restored into `minio_custom_test` and `flood_metrics_test`.
  The raster tiles are rebuilt from the NetCDF only when a test needs them (`scripts/testdata/rebuild_tiles.py`, `US-126`).
  See [[test-dataset]] and ADR-017.
- **Java tests.** `mvn -B -f java/time-aware-routing/pom.xml test` runs the module's 14 files under `src/test/java` (13 test classes and one helper).
  The CI job in `.github/workflows/java-module.yml` builds the pinned GraphHopper commit first, because 12.0-SNAPSHOT is not on Maven Central.
- **Frontend tests.** `floodmap/graphhopper-maps/test/` holds Jest tests (for example `Converters.test.ts`).
- **Contract test.** `test_core_contract.py` checks [[core-output-contract]] against the live schema.
  `test_backend_reads_contract_tables.py` fails when the backend reads a table outside the contract.
  `test_reader_role.py` checks that each reader role can read its tables and nothing else.
  The workflow `flood-areas-test.yml` runs the flood area tests against a PostGIS service, and `restore-snapshot-test.yml` runs the restore script against a throwaway PostGIS.
- **Manual DAGs.** `flood_forecast_consecutive_state_test` runs two consecutive rain events through the
  production steps and publishes them under one run name, so the frontend shows both (D-007).
  `calculate_depth_manual_test` runs one depth calculation.
- **Server tools.** The soak, routing proof, edge table timing, storage reading, test database restore, and rain replay
  (section 4.13 and 4.12).
- **Scratch space.** `marie-curie/` (repository root) holds experiments. Git tracks only its README. An idea
  from `artifacts/raw/ideas/` graduates out of it into a script, DAG, or concept page once it works. Original
  design: the folder was named `einstein/`.
- **Test coordinates.** Every test that uses a coordinate must lie inside the 3Di model border
  (longitude 105.7015 to 105.7971, latitude 20.9754 to 21.0269). `.claude/CLAUDE.md` holds the rule.
- Retired: `floodmap/valhalla-flood-road-test/` no longer exists (ADR-002). The DAG `flood_forecast_pipeline_test`
  (`dags/test_dag.py`) was deleted on 2026-09-24 (D-003).

## 10. Architecture decision records

### ADR-001: Replace raster PNG tiles with vector polygon tiles for map visualization

**Date:** 2026-09-22 **Status:** Accepted, shipped
**Context:** The original design's tile generator rendered each depth GeoTIFF's colour ramp to raster PNG
tiles (`gdal2tiles`), served from S3 and CloudFront. A raster tile carries only colour. It cannot expose
distinct segment states, per-pixel depth values, or a data audit trail without a separate lookup.
**Decision:** Dissolve each timestep's depth raster into banded polygons (GRASS GIS, inside `flood_extent.py`),
cut those polygons into Mapbox vector tiles (`.pbf`), and store the same polygons in PostGIS
(`flood_extent_polygon`) as an audit copy. Serve the `.pbf` tiles from MinIO behind nginx.
**Consequences:** The overlay is attribute-bearing vector geometry. The storage moved from S3 and CloudFront to
self-hosted MinIO. `/flood/runs` and `/flood/timesteps` replace the single `/flood/tiles/{z}/{x}/{y}` redirect.
GRASS GIS is a hard runtime dependency (the `Dockerfile` installs `grass-core`), and no GRASS-free rewrite is
planned. Only the first 2 steps of each run get tiles (`FLOOD_EXTENT_TILE_STEPS`), and the newest 8 runs stay
(`FLOOD_EXTENT_KEEP_RUNS`). Detail in [[minio-flood-extent-pipeline]].
**Update (2026-10-13):** the tile build left `flood_mapping_full` on 2026-10-10 and runs as the DAG `flood_tiles` (ADR-018).

### ADR-002: Replace Valhalla with GraphHopper as the flood routing engine

**Date:** 2026-09-08 (commit `6394e27`) **Status:** Accepted, shipped
**Context:** The original design named Valhalla as the flood routing engine: a flood-weighted graph
re-weighted each cycle. The commit message gives only "embed flood as a cost factor more effectively". The
team's actual reason is not recorded. The likeliest cause is that Valhalla has no graded area penalty
([[BL-011-routing-not-time-aware|routing-not-time-aware]], "Valhalla, 2026-09-29"). That ranking is inference.
**Decision:** Replace Valhalla with GraphHopper, fronted by a new `server.py` that derives GraphHopper's
`custom_model` from PostGIS instead of Valhalla's `linear_cost_factors`.
**Consequences:** `POST /route` and `GET /flood/areas` are served by the GraphHopper-fronting backend. The
active frontend is `graphhopper-maps`. Vehicle thresholds moved to a trimmed fork of the Valhalla scripts
(`flood_utils.py`). `custom_model.areas` and `linear_cost_factors` are not wire-compatible. The prior Valhalla
implementation was retired and then deleted in commit `5d1a606` on 2026-09-23. Original text of this ADR said
it stayed on disk untouched. Detail in [[graphhopper-backend]].

### ADR-003: Compute road depth from stored raster tiles and store the deepest sample

**Date:** 2026-09-24 and 2026-09-25 (D-001, D-006) **Status:** Accepted, shipped.
Superseded by ADR-014 on 2026-10-13.
**Context:** The GeoJSON chain sampled depth from `depth.tif` files at `SAMPLE_RATE=20`, so each old depth was
the top-left pixel of a 20 m cell. About half of the old wet slivers were dry along the road itself (D-005).
**Decision:** Load the depth rasters into `flood_depth_raster_tile` (`9b_load_depth_raster`) and let
`flood_on_roads` write `flood_road_values` in place from those tiles, one row per road piece in
`road_segment`, with the deepest 1 m sample in `depth` and no second column (D-001, D-006).
**Consequences:** Writing in place left routing unchanged, so the reading side needed no change. The mean
missed 39 to 168 pieces per vehicle and run where the road reached the limit, and the maximum missed 0 to 5
(D-005 comparison on two real runs). Routing is more cautious than the old pipeline, for example 1,084 more
closed pieces for the motorbike in run 164803. The mean of a piece cannot be recovered without recomputing from
the tiles. D-002 and D-005 are superseded. The GeoJSON scripts left the DAG on 2026-09-24 and were deleted on
2026-09-29. Detail in [[flood-on-roads]].
**Superseded (2026-10-13):** ADR-014 merged this sampler into the edge depth build.
The task `flood_on_roads`, the scripts `load_road_segments.py` and `flood_on_roads.py`, and the tables `road_segment`, `flood_road_values`, `flood_road_file`, and `flood_road_values_shadow` were deleted.
The decision to compute depth from the stored raster tiles stands.
The deepest 1 m sample along the road also stands, now per graph edge in `9c_build_edge_depth_table`.
The page [[flood-on-roads]] is archived.

### ADR-004: Remove the `flood-results-full` bucket

**Date:** 2026-09-24 (D-004) **Status:** Accepted, shipped. The server bucket was deleted on 2026-09-25.
**Context:** Only the retired GeoJSON tasks 7 and 8 used the bucket.
**Decision:** Remove it from `compose.yml`, `.env.example`, the README, the docs, and the tests, and delete the
bucket and its 15 objects (14.7 MB) on the server.
**Consequences:** MinIO stays for the flood tiles. The original design's list of buckets loses one. The GeoJSON
files are not needed for routing, tiles, or points.

### ADR-005: Drop `background_cycle` and the 24-bar institution histogram

**Date:** 2026-10-01 (D-009) **Status:** Accepted
**Context:** The pipeline runs one cycle, the 15-minute `flood_mapping_full`, and no DAG ever produced
`background_cycle` data.
**Decision:** Do not run `background_cycle`. Drop every story that needs its output. `US-021` is dropped.
**Consequences:** Bars 7 to 24 of the institution histogram have no source, so the histogram cannot be built as
specified (section 4.9). The schema keeps the `background_cycle` enum value, the `background_forecast_depth`
table, and the bars 7 to 24 constraint, all unused. Revisit if a forecast beyond the 2-hour window is wanted.

### ADR-006: Run the cycle every 15 minutes behind a rain gate

**Date:** 2026-09-25 (agreed in the brainstorm of [[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]]) **Status:** Accepted, shipped.
The vault has no D-entry for the user's approval, so the approval is unverified.
**Context:** The map must show "now" and the next two hours, and the routing option chosen in
[[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]] needs a tile for every "now". The original design refreshed roughly every 30
minutes, which leaves gaps.
**Decision:** Start a run on every 15-minute clock slot, simulate 2 hours with 900 s output steps (8 steps),
save the state at 900 s, and run the full pipeline only when the forecast reaches 5 mm/h. Tile the first 2 steps
and load all 8 into the raster table.
**Consequences:** Runs overlap, so the DAG allows 2 active runs and pools serialize the heavy tasks. Every
simulating run is a real 3Di run, which costs money (ADR-012). A dry cycle ends as a success and counts as a
success for the cold start rule. Whether the map shows "now" or the nearest forecast step by default stays open
in [[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]].
**Update (2026-10-13):** the gate also stays open while an earlier flood stands on the roads (`BL-028`, `US-101`), because in the replay of 2026-10-10 the gate alone would have skipped 4 of 46 slots of a storm.
The 5 mm/h threshold stays (D-037).
Each decision writes a `forecast_mode` row (ADR-015), and a stale-run guard skips a run whose slot is older than 120 minutes (`US-139`).
The owner marked `BL-010` resolved on 2026-10-10.

### ADR-007: Store 3Di NetCDF values in TimescaleDB with compression and 48-hour retention

**Date:** 2026-10-05 (`US-066`) **Status:** Accepted, shipped.
Superseded on 2026-10-10 by D-018 and D-022 (`US-095`).
**Context:** A same-named table on `storage-postgres` had no retention and reached 56 GB (about 143 million
live rows) during the 48-hour soak ([[BL-022-docker-data-vhdx-fills-c-drive-again|docker-data-vhdx-fills-c-drive-again]]).
**Decision:** Move `netcdf_values` to a TimescaleDB hypertable with a 6-hour compression policy and a 48-hour
retention policy, and deduplicate the mesh into `mesh_elements`. Drop the old table without a full historical
backfill.
**Consequences:** The DAG writes to TimescaleDB directly. The data of `netcdf_values` older than 48 hours is
gone by design. Detail in [[timescaledb-schema]].
**Superseded (2026-10-13):** the owner retired the NetCDF ingest in Sprint 11 (D-018, `US-095`).
The commit that removed the task `3b_upload_netcdf_postgres` and its scripts is dated 2026-10-09, and the five tables were dropped on the server on 2026-10-10, before the archive was proven on real rain (D-022).
The reason was that `netcdf_values` held 5,378 MB and grew about 13 MB per run, and the archived NetCDF file is the source of truth (ADR-020).
The tables `netcdf_values`, `mesh_elements`, and `netcdf_variable_catalog` no longer exist, in TimescaleDB or in `storage-postgres`.
The `timescaledb` container stays and holds the depth history (ADR-019).
Until the archive runs on real rain, no copy of the per-timestep 3Di values is kept (D-022).

### ADR-008: Route with sticky closure in a Java module on GraphHopper

**Date:** 2026-09-29, with wording confirmed 2026-10-02 **Status:** Accepted, built.
The flag is on since 2026-10-12.
**Context:** A `custom_model` judges every road at one timestep, so a road that is dry now and flooded on
arrival is not avoided. GraphHopper's `Weighting` carries no arrival time, a `custom_model` has no time
dimension, and the engine survey of 2026-09-29 found no engine that does it off the shelf
([[BL-011-routing-not-time-aware|routing-not-time-aware]]).
**Decision:** Build a Java module (`TimeAwareDijkstra`, `StickyClosure`) that carries the arrival time in the
search, and read depth by edge id from the edge depth table. A road is closed for an arrival when a forecast
step in `[departure, arrival + margin]` has a depth at or above the vehicle's limit. Steps before the departure
are ignored (sticky from the departure). The margin is 600 s. The user set the latency limit at 2 times the
baseline of `US-046`.
**Consequences:** The rule is conservative: a road that drained stays closed for a later traveller. A Python
reference and checker (`scripts/routing_reference/`) verify the engine. The backend falls back to the
`custom_model` request on any engine failure. The server proof (`US-055`) is In progress, and the flag stays
off until it has evidence. Detail in [[sticky-routing-reference]].
**Update (2026-10-13):** the evidence came and the flag is on.
The owner kept sticky closure as the engine's rule on 2026-10-10 (D-023), set `TIME_AWARE_ROUTING` on for `floodmap-backend` on 2026-10-12 (D-034), and the server proof closed (`US-055`).
The replay measured that single-timestep routes meet a road that is too deep on arrival in 307 of 3,911 cases, 7.8 percent (D-031).
The engine also returns two paths, a recommended route under the precaution depth of half the limit and the route at the hard limit (D-021).
In `DEMO` mode the route skips the engine (ADR-015).

### ADR-009: Keep edge depth tables in a Docker named volume with an atomic pointer

**Date:** 2026-10-05 (`US-042`) **Status:** Accepted, shipped
**Context:** The readers are a Java engine and a Python backend in other containers.
**Decision:** Store one file per run in the volume `edge-depth-tables`, and publish by renaming a `latest`
pointer file. Do not use MinIO and do not use a folder under `DATA_HOST_PATH`.
**Consequences:** MinIO would give the readers an S3 client and credentials to keep. A folder under
`DATA_HOST_PATH` sits on the D: drive behind Windows file sharing, where replacing an open file can behave
differently from Linux. A rename inside the volume lets a reader see the old name or the new one, never an
empty file. Only the worker writes, and the readers mount the volume read-only.
**Update (2026-10-13):** the volume keeps the newest 8 files, the count of the depth rasters (D-033, `US-112`), and every prune keeps the file of the pinned demo run (ADR-015).

### ADR-010: Run the routing tasks in a separate DAG triggered by an Airflow asset

**Date:** 2026-10-06 (`US-073`) **Status:** Accepted, shipped on the server.
Changed by ADR-014, ADR-018, and ADR-019 on 2026-10-13.
**Context:** The routing tasks `load_road_segments`, `flood_on_roads`, and `9c_build_edge_depth_table` sat in
the core DAG. A red routing task turned the core run red, and `hotstart_policy` lets a run hotstart only when
the previous slot succeeded, so a routing failure forced cold starts.
**Decision:** Move them to the DAG `routing_adapter`, scheduled on the asset `flood_depth_raster_tile` that
`9b_load_depth_raster` emits with `{"run_ts": ...}`. Task `9c` depends only on `9b`, so an asset trigger adds
seconds to its timing. Routing tasks share a one-slot pool.
**Consequences:** A routing failure leaves the core run green. The routing tasks run only after a simulating
run, so pausing the core DAG stops `routing_adapter`. The 5-minute limit of `US-045` for 9c is not yet measured
under the asset trigger. A TaskGroup in the same DAG is the fallback.
**Update (2026-10-13):** the DAG `routing_adapter` has one task, `9c_build_edge_depth_table`.
The tasks `load_road_segments` and `flood_on_roads` were deleted (ADR-014).
Task `9c` now also emits the asset `edge_depth`, which starts the DAG `flood_history` (ADR-019).
The tile build moved the other way, out of the core DAG into its own DAG on its own asset (ADR-018).
The 5-minute limit of `US-045` was met: a run took 148 s from `3_calculate_depth` to the end of `9c` on 2026-10-13.
A routing failure still leaves the core run green, so no TaskGroup was needed.

### ADR-011: Read the core's output through a stated contract and a read-only role

**Date:** 2026-10-06 and 2026-10-07 (`US-071`, `US-072`, `US-075`) **Status:** Accepted, shipped
**Context:** The backend connected to PostGIS as the pipeline's own user, so it could write. The user wants the
system ready for other consumers without building them.
**Decision:** Write the contract ([[core-output-contract]]) and a test that compares it with the live schema.
Run the backend as `routing_reader`, which has `SELECT` on the contract tables only. Fail a test when the
backend reads a table outside the contract. Build no read API and no per-run export until a second consumer
shows the shape it wants.
**Consequences:** `road_segment` is unreadable by the backend, and a new table the pipeline creates is not
readable by the role until the role script runs again. Vehicle limits have one owner, `VEHICLE_PROFILES`
(`US-074`).
**Update (2026-10-13):** the contract grew to nine tables and `road_segment` no longer exists (ADR-014).
`routing_reader` reads 9 tables and `analysis_reader` reads 4, each from its own list in the contract page (`US-107`).
The role script runs in the worker, which mounts the parser and the contract page (`US-132`).
The `analysis` container adds two more roles, `analysis_owner` and `analysis_timescale_reader` (section 4.14).

### ADR-012: A test replay covers 12 hours of rain

**Date:** 2026-10-08 (D-012) **Status:** Accepted
**Context:** Every simulating run is a real 3Di simulation, and the cost grows with the number of runs.
**Decision:** Replay 12 hours, the wettest 12 hours of the storm of 2026-09-16 and 2026-09-17, not the 48 hours of
the October 2025 event. At a gate of 5 mm/h the event gives 42 simulating runs out of 46.
**Consequences:** `US-069` cannot show its 24-hour to 48-hour storage comparison, so its pass condition needs a
decision from the user.
**Update (2026-10-13):** D-015 set the check from hour 6 to hour 12 of the replay, and `US-069` is Done.
The second replay of 2026-10-10 ran the whole storm, and it is kept as the test dataset (ADR-017).

### ADR-013: Build all of Sprint 11 before the next server run and deploy once

**Date:** 2026-10-07 (D-011) **Status:** Accepted
**Context:** A 48-hour run costs a lot, and every story that needs the server can share one run.
**Decision:** Build and test the engine stories and Sprint 11 locally on `modular`, then deploy once and run
the DAG for about an hour.
**Consequences:** The server runs `modular`, which is 212 commits ahead of `main`. A second deploy is the
alternative if the first `rollout.ps1` fails because of the role or the DAG move.

### ADR-014: Keep one sampler and one table for flood depth, keyed by a stable edge key

**Date:** 2026-10-12 (D-038), built through 2026-10-13 (D-042, D-046, D-047) **Status:** Accepted, shipped.
Supersedes ADR-003.
The old tables were dropped on the server on 2026-10-13.
**Context:** Two samplers read the same depth rasters on two geometries.
`flood_on_roads` sampled 35,652 road pieces into `flood_road_values`, and task `9c` sampled 67,833 graph edges into the edge depth file.
The two could drift apart, so the map could show water that the router did not use.
A run that wet no road piece wrote no rows, so the map and the route fallback kept showing the water of an earlier run (`US-115`, `US-116`).
The owner asked for one procedure and one table.
**Decision:** Task `9c_build_edge_depth_table` also writes the wet edges to `edge_depth`, with a registry row in `edge_depth_run` that lists the forecast times of every run, wet or dry.
The table is keyed by `edge_key`, the OSM way id and the position along the way, which the graph export (format 3) and `graph_edge` carry (`US-117`).
Each reader moved to `edge_depth` one at a time: the map overlay and the route fallback (`US-119`), the rain gate and the soak checks (`US-120`), the flood metrics (`US-121`), and the depth history (`US-122`).
Then `flood_on_roads`, `load_road_segments`, `prune_flood_road_values`, and the tables `flood_road_values`, `flood_road_file`, `road_segment`, and `flood_road_values_shadow` were deleted (`US-123`).
**Consequences:** The map overlay and the metrics changed grain from pieces to edges, and a wet edge is drawn whole.
The new overlay covered about 2.2 times the area of the old one on 2026-10-12.
The piece-keyed rows of `depth_history` could not be mapped to edges, so the owner had them deleted (D-042), and the history was rebuilt from the runs in `edge_depth` (D-047).
Task `9c` carries the extra work.
It took 24 s on two real runs and 79.5 s at most over 50 consecutive runs of the test dataset on 2026-10-13, against the revisit trigger of 150 s.
A run took 148 s from `3_calculate_depth` to the end of `9c`.
The answers of `GET /flood/areas`, `GET /flood/points`, and `POST /route` did not change when the old tables were dropped.
The drop freed 377.1 MB and left 11 pipeline tables.
The retention of 24 hours in `edge_depth` replaces the prune of `flood_road_values` (D-017).
Revisit if the stable key cannot be built, the mean time of `9c` passes 150 s, or a reader needs a piece set that `edge_depth` cannot give.

### ADR-015: Serve a forecast mode, pin a demo flood, and route in the demo without the engine

**Date:** 2026-10-10 (D-030) and 2026-10-12 (D-043) **Status:** Accepted, built, deployed on 2026-10-13.
D-043 was a development team decision that the owner has not read.
The demo banner of the frontend (`US-131`) is not built.
**Context:** When no rain is forecast, the map showed no flood, and the pruners removed old runs.
The owner wants the map to show a demo flood in that case, and the depth popup and the routing must use the same flood as the tiles.
**Decision:** The flood map has three modes.
`LIVE` means rain above the gate or a standing flood, with a published step.
`PENDING` means the same gate with no published step yet.
`DEMO` means no rain and no standing flood.
Task `0_check_forecast_rain` writes one `forecast_mode` row per decision, and task `9b_load_depth_raster` moves it from `PENDING` to `LIVE`.
`demo_pin` holds one row, the step with the most wet edges in the stored replay of the storm of 2026-09-16 (run `20261011T001500` on 2026-10-13), and every prune keeps the pinned run.
`GET /flood/mode` answers the mode, and in `DEMO` mode `GET /flood/areas`, `GET /flood/points`, and `POST /route` read the pinned step.
`POST /route` in `DEMO` mode skips the time-aware engine, even with `TIME_AWARE_ROUTING` on, and sends the request with the flood areas of the pinned run (D-043).
**Consequences:** The engine reads only the table that `latest` names and floors the departure to the clock, so it cannot judge a stored step from another day without a change to the Java module and an image rebuild.
The flood areas already accept a pinned run, so the overlay and the route see the same water.
The departure advice of `POST /route/departures` does not change with the mode.
The owner rejected four alternatives: shift the demo onto the real clock, show a slider over the demo, show the demo on the tiles only, and write the warning in Vietnamese.
A test that compares a `LIVE` route with a `DEMO` route uses endpoints that are dry and at least 150 m from the flood (D-044).
Revisit if the demo route must show the departure advice, or the engine can read a pinned table.

### ADR-016: Keep the pipeline tables in schema `public`

**Date:** 2026-10-13 (D-049) **Status:** Accepted.
The decision is the development team's answer to the spike `US-110`, and the owner has not read it.
**Context:** The pipeline tables and Django's tables share the database `minio_custom` and the schema `public`.
A move into its own schema would give a cleaner namespace.
**Decision:** The tables stay in `public`.
A move waits for one of three triggers.
A Django migration or model needs a table whose name a pipeline table has.
A Django model is put over a pipeline table (`managed = False` or `inspectdb`).
A consumer needs a grant on the pipeline tables that its table list cannot give.
**Consequences:** Nothing breaks while the tables stay.
Django manages 14 tables of its own, no model or migration names a pipeline table, and `python manage.py migrate --plan` plans no operation.
One role, `minio_custom`, owns all the tables, and the readers get `SELECT` on a list.
A move changes about 7 files and needs a one-time migration, and it has three risks.
Django and the pipeline writer share the role, so a role-level `search_path` would make `migrate` create Django tables in the new schema.
`to_regclass('forecast_mode')` returns NULL when the schema is not on the path.
The readers need `USAGE` on the schema, and the `ALTER TABLE ... SET SCHEMA` locks must not overlap a run.
Qualifying every query would touch about 70 files.
The cheapest time for a move is after the old road tables are gone, with 11 pipeline tables left instead of 15.
The analysis container is the first case of a separate schema: it owns the schema `analysis` and nothing else (section 4.14).

### ADR-017: Keep a real storm as the test dataset and run the database suites on scratch databases

**Date:** 2026-10-12 (D-039) and 2026-10-13 (D-048) **Status:** Accepted, shipped.
D-048 is a development team decision that the owner has not read.
**Context:** The next core run deletes the NetCDF files after 24 hours, and a replay costs 3Di time.
A throwaway container with synthetic rows did not meet the versions and behavior of production.
A check of the suites found that about 9 of them create and drop tables in `public`, so they cannot share a database with data worth keeping.
**Decision:** The 58 runs of the storm replay of 2026-10-10 are the test dataset, in `data/testdata/storm-2026-10-10/`.
The `results_3di.nc` of each run is the source of truth, read-only, with a manifest and checksums.
The derived tables that existed on 2026-10-12 are saved as a snapshot, and a restore script fills two test databases, `minio_custom_test` in `storage-postgres` and `flood_metrics_test` in `timescaledb`.
Derived data that did not exist, such as the raster tiles, is rebuilt from the NetCDF when a test needs it (D-046).
The command `python3 scripts/testdata/run_db_tests.py` creates one scratch database on each server per run, runs the database suites on them, drops them, and fails when the row counts of the restored test tables change.
**Consequences:** The dataset has no retention, and the production retention does not change.
Rana keeps each result for one month, which is a second copy of the NetCDF files until about 2026-11-09.
A restore takes about 2 minutes and `minio_custom_test` takes 2,628 MB.
On 2026-10-13 the suites gave 753 passed, 0 failed, and 8 skipped on the server, with the dataset unchanged.
The 50-run check of `9c` ran on the dataset, and it is the reason the build time of `9c` is known (ADR-014).
A schema per run with `search_path` was rejected, because an unqualified `DROP TABLE` of a table that the scratch schema lacks would drop the table of `public`.
Revisit if the dataset fills the Docker disk on C:, the model or the graph changes, or the suites move to a schema each.

### ADR-018: Run the flood tile build as its own DAG, started by an asset

**Date:** 2026-10-10 (D-027, `US-103`) **Status:** Accepted, shipped.
The server check passed on 2026-10-10.
**Context:** The tile build sat inside `flood_mapping_full`, so a tile failure or a tile code change touched the simulation DAG.
The owner wanted the visualization separate, as preparation for a 3D view and a building cost estimate.
**Decision:** Task `9_build_flood_tiles` is the one task of the DAG `flood_tiles`.
Task `3b_publish_depth_files` of the core DAG emits the asset `flood_depth_files` with `run_ts` and `depth_dir`, after `3_calculate_depth`, `2c_archive_done`, and `0b_ensure_schema`.
`flood_tiles` runs on that event, and when events fold into one run, every run in them gets tiles.
The input of the build is the depth files.
A second input that read `flood_depth_raster_tile` was coded, measured on 5 paired runs, and lost (`US-104`).
It built no tiles as shipped (`BL-029`), and the owner decided that nothing needs the build off the worker's disk, so the code was deleted on 2026-10-13 (`US-140`).
**Consequences:** A failure of `flood_tiles` does not turn a core run red.
A new consumer of the depth files is its own DAG on the same asset.
The age-based cleanup of the result and depth folders stays in `publish_run`, so `flood_tiles` owns it, and a later consumer must not delete the depth folder.
Revisit if a second consumer needs the files after the 24-hour cleanup, or the worker and the tile build move to different hosts.

### ADR-019: Store the flood history by edge and moment in TimescaleDB for one year

**Date:** 2026-10-10 (D-028, D-032) and 2026-10-12 (D-036, D-042, D-047) **Status:** Accepted, shipped.
`US-106` is Done, and the migration to `edge_key` ran on the server on 2026-10-13.
**Context:** After a storm, the system kept rasters and tiles for 8 runs, and no store held the storm for later analysis.
The industry applications of `EP-21` need the depth of past floods for about a year.
The model's own forecast values are the only source, because no gauge observation enters the pipeline.
**Decision:** `depth_history` in TimescaleDB holds one row per edge and moment.
When two runs cover the same moment, the run with the later `issued_at` wins, and an edge that an earlier run wet and the winning run did not wet has no row.
The table `history_moment` has one row for every moment a run covered, even when no edge is wet.
A moment in `history_moment` with no row for an edge means dry, 0 m, and a moment not in `history_moment` means unknown, for example a slot that the rain gate skipped.
A run that wets no edge records its moments as dry (D-036).
Both tables use 7-day chunks and drop data after 365 days, and `depth_history` is compressed per closed chunk.
The DAG `flood_history` loads each run from `edge_depth` after `9c` commits it, and loading a run again gives the same rows.
**Consequences:** D-032 sized one year of storm days at about 1.3 GB, on the assumption of 11.4 times compression from a sample.
The measured ratio was 9.7 on the whole stored storm and 1.7 on one chunk that holds one run (readings of 2026-10-12).
One run is too little data to judge.
Keeping every forecast for lead-time analysis was rejected for now, and a new story adds it if such an analysis is asked for.
The rows that were keyed by road piece were deleted once (ADR-014).
The backfill loaded the 2 runs of `edge_depth_run` on 2026-10-13, and a second pass gave the same 39,031 rows.
Revisit if an analysis needs more than one year or the forecast error, or the compression on a longer series differs far from the sizing.

### ADR-020: Archive the results of every real-rain run

**Date:** 2026-10-08 (D-016) and 2026-10-13 (D-045) **Status:** Accepted, built.
The real-rain proof is open, and `US-114` is in monitoring until real rain comes (log of 2026-10-13).
**Context:** The cleanup in `flood_tiles` deletes the NetCDF files after 24 hours.
The system kept no store that holds a storm for later analysis.
The NetCDF file is the source of truth, because the depth rasters, the polygons, and the edge depths can be rebuilt from it and the model.
**Decision:** Task `2b_archive_results` copies `results_3di.nc` and a `run_record.json` of each simulating run to an archive folder on the D: drive of the server, only when the rain source is real (Tomorrow.io, not a replay).
The record holds the simulation id, the slot, the rain input, the model id, and the graph hash.
The copy fails loudly when the free space falls under `ARCHIVE_MIN_FREE_GB`, 50 GB (D-037).
A run in real mode counts as the real-rain run for the proof, whether a forecast above 5 mm/h or the standing-flood rule opened the gate (D-045).
**Consequences:** The archive made the NetCDF ingest into TimescaleDB unnecessary, and the ingest was retired (ADR-007).
Each run takes about 7 MB, and the growth over a week is not measured yet.
Two real runs on 2026-10-13 wrote `run_record.json` under the archive.
The first Given of the proof, and the check that the files survive the 24-hour cleanup, are open.
Revisit if the free space of D: falls, or 3Di is found to keep results long enough to re-download (Rana keeps them for one month).

## 11. Future considerations and roadmap

Until 2026-10-10 the plan was four sprints of one week each ([[SP-01-prd-and-backlog|sprint-plan]], [[SP-02-routing-engine-foundations|sprint-plan-2]], [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]).
The work ran ahead of the planned dates, so the first table gives both.
On 2026-10-10 the owner adopted Scrum, retired the four-sprint plans, and set the sprint length to two weeks (D-024, D-026).
The backlog and the current sprint are in `artifacts/TODOS.md`, which is generated from the vault.

| Plan and sprints | Planned dates | Actual start | State on 2026-10-08 |
| --- | --- | --- | --- |
| Plan 1, Sprints 1 to 4: backend prerequisites, raster-first pipeline, frontend depth features, flood metrics | 2026-09-21 to 2026-10-18 | Sprints 2 and 3 on 2026-09-30 | All stories Done except `US-021` (dropped) and `US-034` and `US-033` (moved to later plans) |
| Plan 2, Sprints 5 to 8: baselines, reference, table format, Java module, edge export, depth table, engine core | 2026-10-19 to 2026-11-15 | 2026-10-05 | All stories Done except `US-045` and `US-069` (Backlog, need replay data) |
| Plan 3, Sprints 9 to 11: engine in the backend, departures, advice, rollout, output contract | 2026-11-16 to 2026-12-06 | 2026-10-05 and 2026-10-07 | `US-051` to `US-054` and `US-071`, `US-072`, `US-074`, `US-075` Done. `US-055`, `US-070`, `US-073` pending evidence from the 12-hour replay that ends at 03:00 +07 on 2026-10-09. |
| Plan 3, Sprint 12: frontend recheck against the mockup, rain test environment, core output hygiene | 2026-12-07 to 2026-12-13 | Starts 2026-10-09 | 15 rows, over the size of one week. `US-088` and `US-089` started early. |

The sprints since the adoption of Scrum:

| Sprint | Dates | Goal | State on 2026-10-13 |
| --- | --- | --- | --- |
| Sprint 13 (`SPR-013`) | 2026-10-12 | The foundation of `EP-21` | The owner ended it early on 2026-10-12 (D-040). The goal was reached except `US-106`, which the owner accepted later that day. |
| Sprint 14 (`SPR-014`) | 2026-10-12 to 2026-10-25 | Finish the remaining backend (D-041) | 45 of 47 points are done. `US-114` (2 points) is in monitoring until real rain comes. `US-139` and `US-140` are Done outside the sprint. The frontend stories of `EP-19` are not part of it. |

Open items:

- **Real-rain archive proof.** `US-114` waits for a real run to check that the archive files survive the 24-hour cleanup and to measure the weekly growth (ADR-020).
  A run in real mode counts, whether a forecast or a standing flood opened the gate (D-045).
- **Photon.** The public instance is slow, and most reverse calls time out (`BL-021`, P3).
  `US-141` would host Photon for Vietnam next to the backend, and the owner put it on hold on 2026-10-13.
- **Frontend.** The mockup recheck (`US-076` to `US-085`) and the demo banner (`US-131`) are in `EP-19`, not started.
  The frontend does not read `GET /flood/mode` yet.
- **Industry analysis.** The container `analysis` has its roles and `GET /health` and no analysis application (`EP-21`).
  Measure the compression of `depth_history` again on a longer series (ADR-019).
- **Engine in `DEMO` mode.** The route skips the engine because the engine reads only the table that `latest` names.
  Reading a pinned table needs a change to the Java module and an image rebuild (ADR-015).
- **Schema move.** The pipeline tables stay in `public` until one of three triggers fires (ADR-016).
- **Unbuilt visualization.** A 3D view and a building cost estimate are not built.
  The tile DAG separates the visualization from the core as preparation for them (ADR-018).
- **Server state.** The pause state of the DAGs other than `flood_mapping_full` after 2026-10-08 is unverified (section 3).
- **Unbuilt design.** Everything marked "Designed, not built" remains unbuilt: the citizen app beyond the web
  slice, the council dashboard, the multi-role Redis, the alert engines, push dispatch, NCHMF and gauge input,
  and the fast-track triggers. Build any of them against this file's Built and Designed split.
- **Partner API.** Phase 3's sketch assumed the raster tile design. A partner MVT endpoint would extend the
  built vector-tile pipeline (section 4.2).
- **GRASS GIS dependency.** No GRASS-free rewrite is planned. Track it as an operational dependency if the
  postprocessing environment changes.

Closed since 2026-10-08, and no longer open: the routing rollout and its server proof (`US-055`, `US-045`), the map default (`BL-010`), the storage check (`US-069`), the prune of `flood_road_values` (`US-086`, then ADR-014), and the backend hardening (`US-034`, `US-014`).

## 12. Project identification

- **Project name:** FloodNav (t3-digital-twin repository)
- **Primary contact:** Mai Anh (architecture author and maintainer)
- **Date of last update:** 2026-10-13

## 13. Glossary

- **3Di**: Cloud-based hydraulic simulation engine (`api.3di.live`).
- **ADR**: Architecture decision record. A dated Context, Decision, and Consequences entry.
- **Archive**: The folder that holds `results_3di.nc` and `run_record.json` of each real-rain run (ADR-020).
- **Asset event**: An Airflow 3 signal that a task emits on success.
  `3b_publish_depth_files` emits one for `flood_depth_files`, and `flood_tiles` runs on it.
  `9b_load_depth_raster` emits one for `flood_depth_raster_tile`, and `routing_adapter` runs on it.
  `9c_build_edge_depth_table` emits one for `edge_depth`, and `flood_history` runs on it.
- **Cold start**: A simulation that starts from the template's initial conditions. The opposite of a hotstart.
- **Contract tables**: The tables and files listed in [[core-output-contract]] that other applications may read.
- **`custom_model`**: GraphHopper's JSON cost-graph document, derived per request from PostGIS to grade road
  segments for flood-aware routing.
- **DEMO**: The map mode when no rain is forecast and no flood stands.
  The map, the depth popup, and the route show the pinned demo flood (ADR-015).
  The other modes are `LIVE` and `PENDING`.
- **Dry cycle**: A 15-minute slot where the rain gate finds no interval at the threshold and no flood stands.
  The run ends as a success and skips every later task.
- **`edge_depth`**: The PostgreSQL table with one row per wet edge and forecast time of a run, keyed by `edge_key`.
  `edge_depth_run` lists every run and its forecast times (section 4.11, ADR-014).
- **Edge depth table**: The file `<run_ts>.bin` that holds the flood depth of every GraphHopper edge at every
  forecast step of one run (section 4.11).
- **`edge_key`**: The stable key of a graph edge, `<osm_way_id>:<position along the way>`.
  It survives a re-import of the same OSM file, unlike GraphHopper's `edge_id`.
- **Forecast mode**: The row of `forecast_mode` that each rain gate decision writes: `LIVE`, `PENDING`, or `DEMO`.
- **GRASS GIS**: Open-source GIS toolkit used for raster-to-polygon vectorization of depth rasters.
- **Graph hash**: A SHA-256 over the GraphHopper graph's nodes, edges, and geometry. A table is valid only for the
  graph with the same hash.
- **Hotstart**: A simulation that starts from a 3Di saved state of the previous run.
- **LIVE**: The map mode when the rain gate is open and a step of a run is published (ADR-015).
- **MVT**: Mapbox Vector Tile (`.pbf`), the format the map tile pipeline serves.
- **NCHMF**: Trung tâm dự báo KTTV Quốc Gia, the Vietnamese National Centre for Hydro-Meteorological
  Forecasting.
- **PENDING**: The map mode when the rain gate is open and no step is published yet (ADR-015).
- **Pinned run**: The run named in `demo_pin`.
  Every prune keeps it (ADR-015).
- **Pre-closure time**: The forecast depth 1 hour ahead reaching a vehicle type's hard-block threshold. A
  routing-policy safety buffer distinct from the physical hard-block limit.
- **Rain gate**: The check in `0_check_forecast_rain` that decides whether a slot simulates.
  It opens when the forecast reaches the threshold or a flood stands.
- **Replay**: Running the pipeline on a recorded rain event instead of the live forecast (section 4.12).
- **Road piece (Retired)**: One row of the deleted table `road_segment`, a stretch of road with a `segment_id`.
  A graph edge with an `edge_key` replaced it (ADR-014).
- **Run manifest**: The table `flood_run_output`, with one row for each published output of a run: `depth_raster`, `extent`, or `edge_depth` (section 4.10).
- **Run (`run_ts`)**: One pipeline run, named by the Vietnam local time of its earliest depth file, in the form
  `YYYYMMDDTHHMMSS`.
- **Saved state**: A 3Di snapshot that the next run attaches as its initial condition.
- **Scratch database**: A database that a test run creates on each server and drops afterward (ADR-017).
- **Stale run**: A run whose slot is older than `FLOOD_STALE_RUN_MINUTES`.
  Five tasks skip it (section 4.1).
- **Standing flood**: A flood that is still on the roads after the rain stops.
  The rain gate stays open until the newest 5 runs of `edge_depth` are under 5 cm and no rain is forecast (section 4.1).
- **Step**: One output time of a run. A run has 8 steps, 15 minutes apart.
- **Sticky closure**: The routing rule that closes a road for an arrival when any forecast step from the
  departure to the arrival plus the margin reaches the vehicle's limit (ADR-008).
- **Test dataset**: The 58 runs of the storm replay of 2026-10-10, kept with their NetCDF files and restored into test databases (ADR-017).
- **`td_limit_cm`**: The depth in centimetres at which a vehicle profile cannot pass, set per profile in
  GraphHopper's `config.yml`.
- **Time-aware engine**: The Java module `java/time-aware-routing` that routes with the arrival time.

## 14. Revision history and version control

This file lives in `artifacts/raw/`, which Claude does not edit unless the user approves it. Git tracks
`artifacts/`, so `git log -p` on this file's path is the full history. Keep `last_updated` in the frontmatter
current on every edit, and add a dated bullet below whenever a section changes materially.

**History:**

- 2026-09-23: Rewrote the original `SW Architecture.md` into the C4-style template, folding in ADR-001 (raster to
  vector tiles) and ADR-002 (Valhalla to GraphHopper), and marking every component Built or Designed, not built
  against `compose.yml`'s service list.
- 2026-10-08: Recorded facts read on the server (unpaused DAGs, `TIME_AWARE_ROUTING=false`, `DJANGO_DEBUG`, published
  ports, firewall state, worker variables) with the user's approval to edit this file. A copy of the file before
  this edit is `marie-curie/T3-Digital-Twin_Architecture.before-serverfacts.md`.
- 2026-10-08: Synced with the code at commit `db99bc1` on the branch `modular`, with the user's approval to edit
  this file. Added the markers Built, not scheduled, Retired, and Dropped. Added sections 4.10 to 4.13 and
  ADR-003 to ADR-013. Corrected the project tree, the container list, the data stores, the deployment, the
  endpoint list, and the roadmap. Replaced NCHMF and gauge input with the Tomorrow.io rain input that the code
  uses and marked the originals Designed, not built. A copy of the file before the sync is
  `marie-curie/T3-Digital-Twin_Architecture.before-sync.md`, which is scratch space and can be deleted.
- 2026-10-13: Synced with the code on the branch `modular`, with the owner's approval to edit this file in place.
  Reflected D-017 to D-050: the single sampler and the table `edge_depth` (D-038), the retired NetCDF ingest, the new DAGs `flood_tiles` and `flood_history`, the container `analysis` and its roles, the forecast mode and the pinned demo flood, the standing-flood rule and the stale-run guard, the results archive, the nine-table contract, the soak `roads` check, and the test dataset with its scratch databases.
  Added section 4.14 and ADR-014 to ADR-020, and marked ADR-003 and ADR-007 superseded.
  A copy of the file before this edit is `marie-curie/T3-Digital-Twin_Architecture.before-2026-10-13.md`.
