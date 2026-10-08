---
date: 2026-09-23
type: concept
status: active
tags: [architecture, source-of-truth, floodnav]
related: ["[[T3-Digital-Twin_Architecture]]", "[[architecture-block-diagram]]", "[[minio-flood-extent-pipeline]]", "[[graphhopper-backend]]", "[[storage-backend-django-layer]]", "[[3di-simulation-orchestration]]", "[[routing-depth-threshold-model]]", "[[core-output-contract]]", "[[edge-depth-table-format]]", "[[sticky-routing-reference]]", "[[flood-on-roads]]", "[[decision-log]]", "[[sprint-plan]]", "[[sprint-plan-2]]", "[[sprint-plan-3]]"]
last_updated: 2026-10-08
---
# FloodNav architecture

Working copy of `artifacts/raw/SW Architecture.md`, rewritten into the C4-style template at
`artifacts/raw/ideas/architecture.md-howto/Architecture template.md` (Project structure, System
context, Container diagram, Core components, Data stores, External integrations, Deployment,
Security, Development and testing, ADRs, Roadmap, Glossary). Two early decisions are folded in
directly: map tiles moved from raster PNG to vector polygons (ADR-001), and routing moved from
Valhalla to GraphHopper (ADR-002).

On 2026-10-08 this file was synced with the code at commit `db99bc1` on the branch `modular`. The
branch `main` does not contain most of what this file marks Built. `git log --oneline main..modular | wc -l`
printed 212 on that date.

Every component carries one of four markers:

- **Built.** A `compose.yml` service, a DAG task, a script that a DAG calls, or an endpoint exists at
  the commit above and the code was read.
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
│   ├── flood_mapping_dag.py       # DAG flood_mapping_full, every 15 minutes: rain gate, 3Di run, depth, tiles, raster load
│   ├── routing_adapter_dag.py     # DAG routing_adapter, runs on the asset event of task 9b
│   ├── core_assets.py             # Asset FLOOD_DEPTH_RASTER, the "run published" signal
│   ├── flood_forecast_state_test_dag.py   # Manual two-event hotstart test (flood_forecast_consecutive_state_test)
│   ├── calculate_depth_manual_test_dag.py # Manual depth test (calculate_depth_manual_test)
│   └── initial_wl_dag.py, dummy_initial_wl_dag.py, manholes_dag.py   # Older water-level DAGs, not part of the 15-minute cycle
├── scripts/                       # Python pipeline code, run by Airflow tasks
│   ├── create_simulation.py       # Rain gate, 3Di run, saved states (hotstart), cold start
│   ├── threedi_client.py, download_result.py, netcdf_input.py, calculate_depth.py, hotstart_policy.py
│   ├── database/                  # DDL scripts, netcdf_to_pg.py, create_routing_reader_role.py
│   ├── flood_extent/              # flood_extent.py (GRASS raster to polygon), publish.py (MinIO and PostGIS), raster_load.py
│   ├── roads/                     # load_road_segments.py (road_segment table)
│   ├── flood_roads/               # flood_on_roads.py (flood_road_values), compare_with_old.py
│   ├── edge_depth/                # build_edge_depth.py, publish_edge_depth.py, edge_depth_table.py, graph_edges.py
│   ├── flood_metrics/             # metrics.py, extract_run.py (no DAG task calls them)
│   ├── routing_reference/         # Slow reference and checker for sticky closure routing
│   ├── routing_proof/             # Server proof of the routing engine, rollout.ps1
│   ├── backend_soak/, pipeline_margins/, storage_check/   # Soak, timing, and storage checks
│   ├── rain_replay.py, rain_env/replay.ps1, rain_events/  # Rain replay tooling and event files
│   ├── initial_wl/, manholes/     # Water-level scripts used by the older DAGs
│   └── test_*.py                  # Tests of the scripts at the top level
├── floodmap/
│   ├── graphhopper-flood-road/    # backend/ (server.py), graphhopper/ (config.yml, custom_model files), scripts/flood_utils.py
│   └── graphhopper-maps/          # Frontend: vendored GraphHopper Maps fork, src/floodmap/, nginx.conf
├── java/time-aware-routing/       # Maven module and Dockerfile for the time-aware GraphHopper image
├── minio_custom/                  # storage-backend (Django, JWT, boto3) and storage-frontend (Vite, React)
├── test/                          # Pytest suite for the DAGs and the 3Di scripts
├── marie-curie/                   # Disposable scratch space, not tracked by git except its README
├── artifacts/                     # This Obsidian vault
├── .github/workflows/java-module.yml   # CI for the Java module
├── Dockerfile, requirements.txt   # Airflow image (Airflow 3.1.7, GDAL 3.6.2, GRASS GIS, Tesseract)
└── compose.yml                    # Full service definition, runs on the remote Docker host
```

Original design: the scratch folder was named `einstein/`. Commit `5d1a606` (2026-09-23) renamed it
to `marie-curie/`. The retired folder `floodmap/valhalla-flood-road-test/` was deleted in the same
commit (ADR-002). The GeoJSON scripts `scripts/extract_geojson.py` and `scripts/mapping/*` were deleted
in commit `0e2abc3` (2026-09-29). The file `scripts/database/geojson_to_pg.py` remains and no DAG calls
it. To regenerate this tree, run `ls` in each folder and `git ls-files | cut -d/ -f1-2 | sort -u`.

## 2. System context

**FloodNav** is a flood navigation and warning platform for Hanoi. The built part is a pipeline that
runs a 3Di hydrodynamic simulation every 15 minutes when rain is forecast, publishes flood depth as map
tiles, rasters, road-piece values and an edge depth table, and serves vehicle-aware routes over them.
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
| Photon (`photon.komoot.io`) | Place search and reverse geocoding for `floodmap-backend` (`place_search.py`, `PHOTON_BASE_URL`). | Built |
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

Services in `compose.yml` at the commit above. [[architecture-block-diagram]] draws them.

| Container | Tech | Status | Responsibility |
| --- | --- | --- | --- |
| `airflow-apiserver`, `airflow-scheduler`, `airflow-dag-processor`, `airflow-worker`, `airflow-init`, `airflow-trigger-flood-mapping` | Apache Airflow 3.1.7, CeleryExecutor | Built | Orchestrate `flood_mapping_full` and `routing_adapter`. `airflow-trigger-flood-mapping` runs `airflow dags unpause flood_mapping_full` once at startup. On 2026-10-08 the server had these DAGs unpaused: `flood_mapping_full`, `routing_adapter`, `calculate_depth_manual_test`, `flood_forecast_consecutive_state_test`, `manholes_waterlevel_rain_pipeline`, and `zz_cold_start_probe`. It had `flood_forecast_pipeline_test`, `flood_initial_wl_pipeline`, and `initial_wl_dummy_pipeline` paused. `calculate_depth_manual_test` and `flood_forecast_consecutive_state_test` have `schedule=None`, so they run only when triggered. `zz_cold_start_probe` has no file in `dags/` in this repository, so its schedule is unverified. The plan for `US-063` calls it an unscheduled probe with 0 runs on 2026-10-02. |
| `airflow-postgres`, `airflow-redis` | PostgreSQL 16, Redis 7.2 | Built | Airflow's metadata database and Celery broker. Not the multi-role Redis described later in this table. |
| `graphhopper` | Image `graphhopper-time-aware:local`, built from `java/time-aware-routing` on the host | Built | Flood-weighted routing engine with the time-aware search (ADR-002, ADR-008). Replaced the Valhalla design. The engine was deployed and tested on the server on 2026-10-07. At rest on 2026-10-08, `floodmap-backend` reads `TIME_AWARE_ROUTING=false`, so ordinary live routing is still single-timestep. |
| `floodmap-backend` (`floodmap/graphhopper-flood-road/backend/server.py`) | Python standard library `ThreadingHTTPServer`, psycopg2 pool | Built | Derives GraphHopper's `custom_model` from PostGIS, proxies GraphHopper, serves `/flood/*` and `/route/departures`. |
| `flood-routing-frontend` (`floodmap/graphhopper-maps`) | TypeScript, vendored GraphHopper Maps fork, nginx | Built | Map and routing UI. Renders vector `.pbf` tiles from MinIO and sends route requests. |
| `minio`, `minio-init` | MinIO `RELEASE.2025-09-07T16-13-09Z` | Built | Buckets `initial-wl`, `manholes-data`, `flood-extent`. Replaced the S3 and CloudFront design (ADR-001). |
| `storage-postgres` | PostgreSQL 17 with PostGIS 3.5 (`imresamu/postgis:17-3.5`) | Built | The contract tables (section 4.10), `road_segment`, `graph_edge`, `graph_edge_export`, and `minio_custom`'s role and access tables. |
| `timescaledb` | TimescaleDB 2.30.1 on PostgreSQL 17 | Built | The 3Di NetCDF values, with compression and 48-hour retention (ADR-007). Replaced the Designed TimescaleDB of the original design, whose histogram tables stay empty (ADR-005). |
| `storage-backend`, `storage-frontend` (`minio_custom/`) | Django REST with JWT, Vite and React | Built | Human-operator UI over MinIO buckets. Separate from the pipeline's own bucket use. See [[storage-backend-django-layer]]. |
| Docker volume `edge-depth-tables` | Docker named volume | Built | The edge depth files. The Airflow worker writes. `graphhopper` and `floodmap-backend` mount it read-only (ADR-009). |
| Redis (task queue, pub-sub bus, short-TTL cache) | Redis | Designed, not built | Would fan out postprocessing work, publish cycle-completion events, and cache API responses. |
| Citizen-facing REST API, as a container distinct from `floodmap-backend` | n/a | Designed, not built | `floodmap-backend` covers routing, map listing, point and route depth. Alerts, community reports, and the dashboard endpoints do not exist. |
| User Location Store | n/a | Designed, not built | User GPS and consent mode. |
| Mobile app, city council dashboard | n/a | Designed, not built | See sections 4.9 and 4.10. |

**Key data flows (built).** Tomorrow.io feeds the rain gate and the 3Di run in `flood_mapping_full`.
`3_calculate_depth` produces `depth_*.tif` (8 per run). Three tasks read those files. `3b_upload_netcdf_postgres`
writes the raw results to TimescaleDB. `9_build_flood_tiles` writes `flood_extent_polygon`,
`flood_extent_step`, and the `.pbf` tiles in MinIO. `9b_load_depth_raster` writes `flood_depth_raster_tile` and emits
the asset event `FLOOD_DEPTH_RASTER`. That event starts `routing_adapter`. Its tasks `load_road_segments`,
`flood_on_roads`, and `9c_build_edge_depth_table` write `road_segment`, `flood_road_values`, and the edge depth
file. `floodmap-backend` reads the contract tables as the read-only role `routing_reader`, and reads the
edge depth file. It serves graded routes, departure advice, and depth lookups. `flood-routing-frontend` loads
tiles from MinIO through nginx and sends requests to `floodmap-backend`.

### Block diagram

[[architecture-block-diagram]]

## 4. Core components

### 4.1 Simulation pipeline (Built)

One Airflow DAG, `flood_mapping_full`, runs the cycle. It has the schedule `*/15 * * * *`,
`catchup=False`, and `max_active_runs=2`, so a run that takes longer than 15 minutes overlaps the next
slot. Three Airflow pools limit concurrency: `threedi_trigger` (2 slots), `depth_calc` (1), and
`routing_adapter` (1). An operator creates them once by hand (README, "Create the Airflow pools").

The DAG has 8 tasks:

```
0_check_forecast_rain --(dry)--> run ends successfully, every later task skipped
        |
      (rain)
        v
1_trigger_simulation --> 2_download_results --> 3_calculate_depth --> 9_build_flood_tiles
        |                        |                      |
        |                        v                      +--> 9b_load_depth_raster (emits FLOOD_DEPTH_RASTER)
        |               3b_upload_netcdf_postgres
        v
0b_ensure_schema --> 3b, 9, 9b
```

- **Rain gate.** `0_check_forecast_rain` reads the Tomorrow.io forecast for the next 2 hours
  (`FLOOD_RAIN_LOOKAHEAD_HOURS`). The run continues only when an interval reaches
  `FLOOD_RAIN_THRESHOLD_MM_HR` (default 5 mm/h). A dry cycle ends as a success. A forecast with no
  intervals raises an error, because an empty answer is not a dry cycle.
- **Run shape.** Each run starts at its 15-minute clock slot, simulates `SIMULATION_DURATION` seconds
  (default 7200) with an output interval of `UPDATE_INTERVAL` seconds (default 900), and skips output
  step 0. The result is 8 depth steps per run.
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
files per run (filenames in Vietnam local time, UTC+7). Original design: 25 files per cycle. Four
consumers read the depth files or results. Routing and map display run on different pipelines and
cadences by design. This is not an incomplete migration. See [[minio-flood-extent-pipeline]].

| Consumer | Reads | Writes | Serves |
| --- | --- | --- | --- |
| `9_build_flood_tiles` (`flood_extent.py`, GRASS GIS, via `publish.py`) | Depth files, first `FLOOD_EXTENT_TILE_STEPS` steps (default 2) | `flood_extent_polygon`, `flood_extent_step`, MinIO `flood-extent/runs/<run_ts>/<timestep>/{z}/{x}/{y}.pbf` | Map overlay (`GET /flood/runs`, `GET /flood/timesteps`) |
| `9b_load_depth_raster` (`raster_load.py`) | Depth files, all 8 steps | `flood_depth_raster_tile` (EPSG:4326, 256 by 256 pixel tiles) | `GET /flood/points`, `POST /flood/forecast`, `POST /flood/profile`, and the inputs of `routing_adapter` |
| `routing_adapter` task `flood_on_roads` | `flood_depth_raster_tile`, `road_segment` | `flood_road_values` | Routing grade (`flood_areas.derive_areas`, `POST /route`, `GET /flood/areas`) |
| `routing_adapter` task `9c_build_edge_depth_table` | `flood_depth_raster_tile`, `graph_edge` | `<run_ts>.bin` in the volume `edge-depth-tables` | Time-aware engine and `POST /route/departures` |
| `3b_upload_netcdf_postgres` (`netcdf_to_pg.py`) | The downloaded `.nc` file | TimescaleDB `mesh_elements`, `netcdf_variable_catalog`, `netcdf_values` | No reader outside `scripts/database/` |

Original design: the road-depth chain read the depth files itself (`extract_geojson.py` and
`scripts/mapping/*`, then `geojson_to_pg.py`, then `flood_road_values`). The raster-first pipeline
replaced it. The routing tasks now read the stored raster tiles (ADR-003).

### 4.3 Filename-to-UTC conversion (Built)

`calculate_depth.py` writes filenames in Vietnam local time (UTC+7). `publish.valid_time_utc()` converts
that to UTC before it writes `valid_time_utc` in `flood_extent_polygon`, `flood_extent_step`, and
`flood_depth_raster_tile`. `flood_extent_runs.list_timesteps` converts back to local time for `GET
/flood/timesteps`, because MinIO's folder names stay keyed by the local-time string. A wrong conversion in
either direction makes the endpoint return a time that matches no tile, off by exactly 7 hours.
`flood_road_values.timestamp` and `forecast_time` are the exception. They store UTC+7 without an offset
([[core-output-contract]], "Time convention").

### 4.4 Postprocessing workers from the original design

The original whiteboard design specifies a metric extractor and four Tier 1 and two Tier 2 workers.

- **Flood metric extractor (Built, not scheduled).** `scripts/flood_metrics/metrics.py` and
  `extract_run.py` compute time-to-peak, recession onset, per-vehicle restoration time, and a pre-closure
  time per road piece and vehicle, plus the forecast depth at T+1h and T+2h (`forecast_depth_1h_m`,
  `forecast_depth_2h_m`). `extract_run.py RUN_TS` writes `flood_segment_metrics` in `storage-postgres`. No DAG
  task calls it, and the DAG does not create that table. See [[flood-metric-extractor]].
- **Tier 1 tile generator (Built).** It is `9_build_flood_tiles` (ADR-001).
- **Tier 1 segment extractor (Built, in a different shape).** It is `flood_on_roads` in `routing_adapter`
  (ADR-003). It has no alert machinery around it.
- **Tier 1 institution histogram builder (Dropped).** ADR-005.
- **Tier 1 user alert engine, Tier 2 segment alert engine, Tier 2 district aggregator (Designed, not built).**
- **Edge depth table builder (Built, not in the original design).** Task `9c_build_edge_depth_table`
  (section 4.11).

### 4.5 Flood Routing Engine (Built, on GraphHopper with a time-aware module)

The original design marked this component a black box on the whiteboard and named Valhalla as the
implementation. The built system replaced Valhalla with GraphHopper (ADR-002) and added a time-aware
search (ADR-008). Full detail is in [[graphhopper-backend]].

- **Image.** `graphhopper` builds from `java/time-aware-routing/Dockerfile`. That file takes the stock
  image `israelhikingmap/graphhopper@sha256:3e79eb33862028cfc58f9d6c162630b68638d6aad790b5a698c854dbbaa7fe32`
  (a 12.0-SNAPSHOT build) as its base by digest, and puts the module's jar first on the classpath. The
  `ch.disable`-in-body behavior that flood-graded routing depends on is undocumented, so the digest stays
  pinned. `compose.yml` keeps the stock image line as a comment for rollback.
- **Grade by `custom_model`.** `floodmap-backend` derives a `custom_model` from PostGIS `flood_road_values`
  through `flood_areas.derive_areas` and forwards the graded request. `GET /flood/areas` and `POST /route`
  call the same function, so the overlay and the routing cannot drift apart. `flood_utils.DEPTH_BANDS`
  grades each road piece in bands of 0.5, 0.75, and 1.0 times the vehicle's limit. The top band (`b4`) is
  impassable. See [[routing-depth-threshold-model]].
- **Time-aware search.** With `TIME_AWARE_ROUTING` on (default `false`), `POST /route` sends a departure to
  the engine. The engine runs `TimeAwareDijkstra` over the edge depth table, applies the sticky closure
  rule, and falls back to the `custom_model` request when the table is missing, stale, or for another
  graph. The response carries `td.status`. The engine was deployed and tested on the server on 2026-10-07
  (`US-055` status note in `artifacts/TODOS.md`: compare, crossings, departures, latency within 2x, and
  scenario-check 32/32 all passed). `scripts/routing_proof/rollout.ps1` turns `TIME_AWARE_ROUTING` on for the
  proof and puts it back off unless run with `-LeaveOn`
  (`artifacts/docs/claude-plan/engine-server-proof-and-rollout.md`, steps 5 to 10). At rest on 2026-10-08 the
  backend reads `TIME_AWARE_ROUTING=false` (default in `compose.yml` and `.env.example`), so ordinary live
  routing still judges every road at one timestep. Whether `-LeaveOn` was used on 2026-10-07 is unconfirmed.
  `US-045` (live timing of task 9c) is still open.
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
| `/flood/areas` | GET | The flood polygons that `POST /route` grades against, for the map overlay |
| `/flood/points` | GET | Depth at one latitude, longitude, and time, from `flood_depth_raster_tile` |
| `/flood/forecast` | POST | Mean depth along a route at 15-minute steps, from `flood_depth_raster_tile` |
| `/flood/profile` | POST | Depth at samples along a route at one timestep |
| `/route` | POST | Flood-graded route, or time-aware route with the flag on (section 4.5) |
| `/route/departures` | POST | Earliest clear departure of the usual route (`US-053`) |
| `/places/search`, `/places/reverse`, `/geocode` | GET | Place search and geocoding through Photon |

The backend connects as the read-only role `routing_reader`, waits up to `FLOOD_DB_POOL_WAIT` seconds
(default 5) for a pooled connection, and answers 503 with `Retry-After` when none frees up.

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
not built. The mockup recheck (`US-076` to `US-085`) is scheduled in Sprint 12.

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
  be built as specified (ADR-005). The tables `institution_histogram_bar`, `background_forecast_depth`, and
  `depth_history` exist in TimescaleDB and stay empty.
- **Route histogram (Built, in a different shape).** `POST /flood/forecast` computes it at query time from
  `flood_depth_raster_tile`, as the original design required, and not from a pipeline worker. The window is
  8 steps of 15 minutes (2 hours), starting at the step that contains `from`. Original design: 8 bars at
  30-minute resolution over 4 hours, computed from PostGIS per-segment forecast depths, served by `GET
  /flood/route/forecast`. The built version reads raster tiles because matching a route to
  `flood_road_values` rows has no stable key (docstring of `flood_forecast.py`).

### 4.10 Core output contract (Built)

The pipeline publishes results that other applications read. [[core-output-contract]] lists them and
`floodmap/graphhopper-flood-road/backend/test_core_contract.py` compares its column tables with the live
database. The contract names five PostgreSQL tables, the edge depth files, and the vector tiles. Routing is
the first consumer.

| Output | Writer | Kept |
| --- | --- | --- |
| `flood_depth_raster_tile` | `9b_load_depth_raster` | Newest 8 runs (`FLOOD_RASTER_KEEP_RUNS`) |
| `flood_extent_polygon` | `9_build_flood_tiles` | Newest 8 runs (`FLOOD_EXTENT_KEEP_RUNS`) |
| `flood_extent_step` | `9_build_flood_tiles` | Newest 8 runs |
| `flood_road_values` | `flood_on_roads` | Every run, no prune found (unverified on the server) |
| `graph_edge` | `9c_build_edge_depth_table` | The loaded graph |
| Edge depth files | `9c_build_edge_depth_table` | Newest 3 runs (`EDGE_TABLE_KEEP_RUNS`) |
| Tiles in `flood-extent` | `9_build_flood_tiles` | Newest 8 runs |

`flood_extent_step` says that a step is fully published. The asset `flood_depth_raster_tile`
(`dags/core_assets.py`) says that every step of a run is in `flood_depth_raster_tile`. Its event carries
`{"run_ts": "<run_ts>"}`. ADR-010 explains why `routing_adapter` runs on it. The role `routing_reader`
(`scripts/database/create_routing_reader_role.py`) can read only these tables (ADR-011).

### 4.11 Edge depth table (Built)

One file holds the flood depth of every GraphHopper edge at every forecast step of one run. The file
`<run_ts>.bin` is edge-major, with a header (`EDGD`, version, step count, edge count, graph hash, run name,
step times) and one 16-bit centimetre depth per edge and step. The real graph has 67,833 edges, so a file
with 8 steps is 1,085,487 bytes. A `latest` text file names the current table. The task writes under a
temporary name and renames, moves `latest` only forward, and keeps the newest 3 files. Both readers refuse a
table whose graph hash differs from the loaded graph's. The byte layout is in [[edge-depth-table-format]].
After a graph re-import, follow [[graph-reimport-procedure]].

Task `9c_build_edge_depth_table` reads the graph export (`graph.json` and `edges.csv`) that
`java/time-aware-routing/export-edges.sh` writes. Airflow cannot run the export because it needs the
GraphHopper image. A build took 42.0 s unloaded and 60.1 s in one `routing_adapter` run on 2026-10-07. The
limit of `US-045`, that 9c ends within 5 minutes of `3_calculate_depth`, is unproven. The one run measured
8.21 minutes (TODOS.md, `US-045`).

### 4.12 Rain replay tooling (Built)

A replay feeds a recorded rain event to the DAG instead of Tomorrow.io, so the pipeline can run under rain
on a dry day. `FLOOD_TEST_RAIN_CSV` and `FLOOD_TEST_RAIN_START` select the event. `scripts/rain_replay.py` has
the subcommands `preview`, `next-slot`, `check`, and `status`. `scripts/rain_env/replay.ps1` has `start`,
`stop`, and `status`. It saves the prior `.env` values, recreates only `airflow-worker`, reads the setting
back from inside the worker, and does not unpause the DAG. The event files are
`scripts/rain_events/hanoi_20251005_48h.csv` (48 hours) and `hanoi_20260916_storm.csv` (12 hours, 53.88 mm,
peak 8.73 mm/h). `replay.ps1 start` ran on the server on 2026-10-08. `stop` has not run yet (`US-089`,
ADR-012).

### 4.13 Verification tooling (Built)

| Tool | Checks |
| --- | --- |
| `scripts/backend_soak/run_soak.sh`, `soak_checks.py` | The 48-hour soak of the backend and a known-answer routing check (`US-034`) |
| `scripts/routing_reference/` | A slow, readable implementation of sticky closure, used as the reference for the Java engine ([[sticky-routing-reference]]) |
| `scripts/routing_proof/rollout.ps1`, `routing_proof.py` | The server proof of the routing engine (`US-055`) |
| `scripts/edge_depth/table_timing.ps1`, `spot_check.py`, `check_tables.py` | Build time, `ST_Value` spot check, and hash agreement of the edge depth table |
| `scripts/pipeline_margins/` | The step-1 margin of every run |
| `scripts/storage_check/read_storage.ps1` | Disk and database sizes |

## 5. Data stores

| Store | Type | Status | Holds |
| --- | --- | --- | --- |
| `storage-postgres` | PostgreSQL 17 and PostGIS 3.5 | Built | `flood_road_values` and `flood_road_file`, `flood_extent_polygon`, `flood_extent_step`, `flood_depth_raster_tile`, `road_segment`, `graph_edge`, `graph_edge_export`, and `minio_custom`'s role and access-group tables |
| `timescaledb` | TimescaleDB 2.30.1 | Built | `netcdf_values` (hypertable, 6-hour compression, 48-hour retention), `mesh_elements`, `netcdf_variable_catalog`. The tables `institution_histogram_bar`, `background_forecast_depth`, and `depth_history` exist and stay empty. |
| MinIO | S3-compatible object store | Built | `initial-wl`, `manholes-data` (private), `flood-extent` (public download, `.pbf` tiles). The bucket `flood-results-full` is Retired (ADR-004). |
| Volume `edge-depth-tables` | Docker named volume | Built | Edge depth files and the `latest` pointer |
| Volume `graphhopper-graph-cache` | Docker named volume | Built | The imported GraphHopper graph |
| `airflow-postgres` | PostgreSQL 16 | Built | Airflow's metadata database |
| `airflow-redis` | Redis 7.2 | Built | Airflow's Celery broker. Not the multi-role Redis below. |
| Redis (task queue, pub-sub, short-TTL cache) | Redis | Designed, not built | Postprocessing fan-out, cycle-completion events, API response cache |
| User Location Store | PostgreSQL | Designed, not built | User GPS and consent mode, read by the user alert engine, which is also unbuilt |
| PostGIS extended schema (dispatch log, community reports, district summary, institutions) | PostgreSQL and PostGIS | Designed, not built | None of these tables exist |
| `flood_segment_metrics` | PostgreSQL table in `storage-postgres` | Built, not scheduled | Output of `extract_run.py`. Exists only if an operator ran `create_flood_metrics_tables.py` (unverified on the server). |

TimescaleDB runs in its own database, `flood_metrics`, with its own credentials (`TIMESCALE_*`).
Original design: TimescaleDB held institution histograms, `background_cycle` forecast series, and depth
history. It holds none of them in practice.

## 6. External integrations

| Service | Purpose | Integration | Status |
| --- | --- | --- | --- |
| 3Di (`api.3di.live`) | Hydraulic simulation | REST API, personal API token | Built |
| Tomorrow.io | Rain forecast | HTTPS, `GET /v4/timelines`, once per cycle | Built |
| NCHMF | Rainfall forecast (GRIB2 or NetCDF) | HTTPS poll | Designed, not built (section 2) |
| Gauge network APIs | Observed water levels for hot start | HTTPS, cycle start | Designed, not built. A scrape of `thoatnuochanoi.vn` exists in `manholes_dag.py` and feeds nothing in the cycle. |
| Photon (`photon.komoot.io`) | Place search, reverse geocoding | HTTPS | Built |
| FCM and APNs | Push alerts | HTTPS or FCM REST | Designed, not built |
| Google Maps | Place search and geocoding for the citizen app | n/a | Designed, not built. Photon fills the role in the web client. |
| GitHub Actions | CI for the Java module (`java-module.yml`) | GitHub | Built |
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
  commands with `;`, not `&&` ([[recreate-remote-services-on-the-remote-host]]).
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
- **Storage.** Docker's disk image `docker_data.vhdx` lives on the host's C: drive and has filled it
  ([[docker-data-vhdx-fills-c-drive-again]]). `DATA_HOST_PATH` and `AIRFLOW_LOGS_HOST_PATH` point task data and
  logs at the D: drive. The edge depth tables use a Docker named volume on purpose (ADR-009).
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
- **Worker environment.** The values on the server match the `compose.yml` defaults (checked 2026-10-08):
  `FLOOD_TEST_RAIN_CSV=/opt/airflow/scripts/rain_events/hanoi_20260916_storm.csv`,
  `FLOOD_TEST_RAIN_START=2026-10-08T08:45:00Z`, `FLOOD_RAIN_THRESHOLD_MM_HR=5`, `FLOOD_RAIN_LOOKAHEAD_HOURS=2`,
  `FLOOD_RAIN_TIMESTEP_MINUTES=15`, `FLOOD_RAIN_CHECK_INTERVAL_SECONDS=900`, `FLOOD_COLD_START_AFTER_BREAK=1`,
  `FLOOD_EXTENT_TILE_STEPS=2`, `FLOOD_EXTENT_KEEP_RUNS=8`, `EDGE_TABLE_KEEP_RUNS=3`, `FLOOD_EXTENT_WORKERS=2`,
  `SIMULATION_DURATION=7200`, and `AIRFLOW_WORKER_CONCURRENCY=4`.
- **Retired-chain leftovers.** The worker also receives `SAMPLE_RATE=20`, `UPDATE_INTERVAL=900`,
  `MIN_DEPTH_THRESHOLD`, `KEEP_LOCAL_GEOJSON`, `LOCAL_GEOJSON_DIR`, `FLOOD_USE_DOWNLOADED_RESULTS`,
  `FLOOD_LOCAL_FALLBACK`, and `VALHALLA_PORT`. A search of the repository (Python, shell, PowerShell, Java,
  TypeScript, YAML, and `.env` files, excluding `artifacts/`) finds no code that reads any of them. Only
  `compose.yml` and `.env.example` mention the first seven, and `VALHALLA_PORT` and `FLOOD_LOCAL_FALLBACK`
  appear nowhere in the repository, so the server's `.env` must set them. They belong to the retired Valhalla
  router and GeoJSON chain. `SAMPLE_RATE` is `20` on the server, while the `compose.yml` default is `1`.

## 8. Security considerations

- MinIO: only the `flood-extent` bucket allows anonymous download (`mc anonymous set download`). The MinIO API
  and console ports bind to `127.0.0.1`, so public access exists only through nginx's proxy.
- `storage-postgres` and `timescaledb` publish their ports on `127.0.0.1` only.
- `graphhopper` (8989), `floodmap-backend` (8010), `flood-routing-frontend` (8082), `storage-backend` (8000),
  `storage-frontend` (5173), and the Airflow API server (8090) publish ports on all interfaces (checked on the
  server 2026-10-08). Windows Firewall is on for the domain, private, and public profiles. Nobody has read its
  rules, so which of these ports it allows from outside is unverified. `server.py` has no authentication code.
  Open item for the user to decide: the Airflow API server on 8090 is reachable on every interface.
- Open item for the user to decide: six DAGs are unpaused on the server, and three of them are manual or probe
  DAGs (`calculate_depth_manual_test`, `flood_forecast_consecutive_state_test`, `zz_cold_start_probe`). The
  first two have `schedule=None`. A person with access to the Airflow API server can trigger any unpaused DAG.
- `floodmap-backend` connects to PostGIS as `routing_reader`, a role limited to `SELECT` on the contract tables
  with no `CREATE` on schema `public` (ADR-011). `docker compose` refuses to start the service without
  `ROUTING_READER_PASSWORD`.
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

- **Python tests.** `git ls-files '*test_*.py' | wc -l` printed 51 files on 2026-10-08. They sit in `test/`
  (DAG graphs, 3Di auth, MinIO bucket routing, NetCDF input, rain gate, state test), beside the code in
  `scripts/`, and in `floodmap/graphhopper-flood-road/backend/` (against a real PostGIS and a stub GraphHopper).
  Run them with `pytest` from the repository root or a test folder. The suite needs PostGIS and GDAL for the
  database and raster tests.
- **Java tests.** `mvn -B -f java/time-aware-routing/pom.xml test` runs the module's 14 test files. The CI job in
  `.github/workflows/java-module.yml` builds the pinned GraphHopper commit first, because 12.0-SNAPSHOT is not on
  Maven Central.
- **Frontend tests.** `floodmap/graphhopper-maps/test/` holds Jest tests (for example `Converters.test.ts`).
- **Contract test.** `test_core_contract.py` checks [[core-output-contract]] against the live schema.
  `test_backend_reads_contract_tables.py` fails when the backend reads a table outside the contract.
- **Manual DAGs.** `flood_forecast_consecutive_state_test` runs two consecutive rain events through the
  production steps and publishes them under one run name, so the frontend shows both (D-007).
  `calculate_depth_manual_test` runs one depth calculation.
- **Server tools.** The soak, routing proof, edge table timing, storage reading, and rain replay
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

### ADR-002: Replace Valhalla with GraphHopper as the flood routing engine

**Date:** 2026-09-08 (commit `6394e27`) **Status:** Accepted, shipped
**Context:** The original design named Valhalla as the flood routing engine: a flood-weighted graph
re-weighted each cycle. The commit message gives only "embed flood as a cost factor more effectively". The
team's actual reason is not recorded. The likeliest cause is that Valhalla has no graded area penalty
([[routing-not-time-aware]], "Valhalla, 2026-09-29"). That ranking is inference.
**Decision:** Replace Valhalla with GraphHopper, fronted by a new `server.py` that derives GraphHopper's
`custom_model` from PostGIS instead of Valhalla's `linear_cost_factors`.
**Consequences:** `POST /route` and `GET /flood/areas` are served by the GraphHopper-fronting backend. The
active frontend is `graphhopper-maps`. Vehicle thresholds moved to a trimmed fork of the Valhalla scripts
(`flood_utils.py`). `custom_model.areas` and `linear_cost_factors` are not wire-compatible. The prior Valhalla
implementation was retired and then deleted in commit `5d1a606` on 2026-09-23. Original text of this ADR said
it stayed on disk untouched. Detail in [[graphhopper-backend]].

### ADR-003: Compute road depth from stored raster tiles and store the deepest sample

**Date:** 2026-09-24 and 2026-09-25 (D-001, D-006) **Status:** Accepted, shipped
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

**Date:** 2026-09-25 (agreed in the brainstorm of [[map-shows-forecast-not-now]]) **Status:** Accepted, shipped.
The vault has no D-entry for the user's approval, so the approval is unverified.
**Context:** The map must show "now" and the next two hours, and the routing option chosen in
[[map-shows-forecast-not-now]] needs a tile for every "now". The original design refreshed roughly every 30
minutes, which leaves gaps.
**Decision:** Start a run on every 15-minute clock slot, simulate 2 hours with 900 s output steps (8 steps),
save the state at 900 s, and run the full pipeline only when the forecast reaches 5 mm/h. Tile the first 2 steps
and load all 8 into the raster table.
**Consequences:** Runs overlap, so the DAG allows 2 active runs and pools serialize the heavy tasks. Every
simulating run is a real 3Di run, which costs money (ADR-012). A dry cycle ends as a success and counts as a
success for the cold start rule. Whether the map shows "now" or the nearest forecast step by default stays open
in [[map-shows-forecast-not-now]].

### ADR-007: Store 3Di NetCDF values in TimescaleDB with compression and 48-hour retention

**Date:** 2026-10-05 (`US-066`) **Status:** Accepted, shipped
**Context:** A same-named table on `storage-postgres` had no retention and reached 56 GB (about 143 million
live rows) during the 48-hour soak ([[docker-data-vhdx-fills-c-drive-again]]).
**Decision:** Move `netcdf_values` to a TimescaleDB hypertable with a 6-hour compression policy and a 48-hour
retention policy, and deduplicate the mesh into `mesh_elements`. Drop the old table without a full historical
backfill.
**Consequences:** The DAG writes to TimescaleDB directly. The data of `netcdf_values` older than 48 hours is
gone by design. Detail in [[timescaledb-schema]].

### ADR-008: Route with sticky closure in a Java module on GraphHopper

**Date:** 2026-09-29, with wording confirmed 2026-10-02 **Status:** Accepted, built, flag off
**Context:** A `custom_model` judges every road at one timestep, so a road that is dry now and flooded on
arrival is not avoided. GraphHopper's `Weighting` carries no arrival time, a `custom_model` has no time
dimension, and the engine survey of 2026-09-29 found no engine that does it off the shelf
([[routing-not-time-aware]]).
**Decision:** Build a Java module (`TimeAwareDijkstra`, `StickyClosure`) that carries the arrival time in the
search, and read depth by edge id from the edge depth table. A road is closed for an arrival when a forecast
step in `[departure, arrival + margin]` has a depth at or above the vehicle's limit. Steps before the departure
are ignored (sticky from the departure). The margin is 600 s. The user set the latency limit at 2 times the
baseline of `US-046`.
**Consequences:** The rule is conservative: a road that drained stays closed for a later traveller. A Python
reference and checker (`scripts/routing_reference/`) verify the engine. The backend falls back to the
`custom_model` request on any engine failure. The server proof (`US-055`) is In progress, and the flag stays
off until it has evidence. Detail in [[sticky-routing-reference]].

### ADR-009: Keep edge depth tables in a Docker named volume with an atomic pointer

**Date:** 2026-10-05 (`US-042`) **Status:** Accepted, shipped
**Context:** The readers are a Java engine and a Python backend in other containers.
**Decision:** Store one file per run in the volume `edge-depth-tables`, and publish by renaming a `latest`
pointer file. Do not use MinIO and do not use a folder under `DATA_HOST_PATH`.
**Consequences:** MinIO would give the readers an S3 client and credentials to keep. A folder under
`DATA_HOST_PATH` sits on the D: drive behind Windows file sharing, where replacing an open file can behave
differently from Linux. A rename inside the volume lets a reader see the old name or the new one, never an
empty file. Only the worker writes, and the readers mount the volume read-only.

### ADR-010: Run the routing tasks in a separate DAG triggered by an Airflow asset

**Date:** 2026-10-06 (`US-073`) **Status:** Accepted, shipped on the server
**Context:** The routing tasks `load_road_segments`, `flood_on_roads`, and `9c_build_edge_depth_table` sat in
the core DAG. A red routing task turned the core run red, and `hotstart_policy` lets a run hotstart only when
the previous slot succeeded, so a routing failure forced cold starts.
**Decision:** Move them to the DAG `routing_adapter`, scheduled on the asset `flood_depth_raster_tile` that
`9b_load_depth_raster` emits with `{"run_ts": ...}`. Task `9c` depends only on `9b`, so an asset trigger adds
seconds to its timing. Routing tasks share a one-slot pool.
**Consequences:** A routing failure leaves the core run green. The routing tasks run only after a simulating
run, so pausing the core DAG stops `routing_adapter`. The 5-minute limit of `US-045` for 9c is not yet measured
under the asset trigger. A TaskGroup in the same DAG is the fallback.

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

### ADR-012: A test replay covers 12 hours of rain

**Date:** 2026-10-08 (D-012) **Status:** Accepted
**Context:** Every simulating run is a real 3Di simulation, and the cost grows with the number of runs.
**Decision:** Replay 12 hours, the wettest 12 hours of the storm of 2026-09-16 and 2026-09-17, not the 48 hours of
the October 2025 event. At a gate of 5 mm/h the event gives 42 simulating runs out of 46.
**Consequences:** `US-069` cannot show its 24-hour to 48-hour storage comparison, so its pass condition needs a
decision from the user.

### ADR-013: Build all of Sprint 11 before the next server run and deploy once

**Date:** 2026-10-07 (D-011) **Status:** Accepted
**Context:** A 48-hour run costs a lot, and every story that needs the server can share one run.
**Decision:** Build and test the engine stories and Sprint 11 locally on `modular`, then deploy once and run
the DAG for about an hour.
**Consequences:** The server runs `modular`, which is 212 commits ahead of `main`. A second deploy is the
alternative if the first `rollout.ps1` fails because of the role or the DAG move.

## 11. Future considerations and roadmap

Plans are four sprints of one week each ([[sprint-plan]], [[sprint-plan-2]], [[sprint-plan-3]]). The work ran
ahead of the planned dates, so the table gives both.

| Plan and sprints | Planned dates | Actual start | State on 2026-10-08 |
| --- | --- | --- | --- |
| Plan 1, Sprints 1 to 4: backend prerequisites, raster-first pipeline, frontend depth features, flood metrics | 2026-09-21 to 2026-10-18 | Sprints 2 and 3 on 2026-09-30 | All stories Done except `US-021` (dropped) and `US-034` and `US-033` (moved to later plans) |
| Plan 2, Sprints 5 to 8: baselines, reference, table format, Java module, edge export, depth table, engine core | 2026-10-19 to 2026-11-15 | 2026-10-05 | All stories Done except `US-045` and `US-069` (Backlog, need replay data) |
| Plan 3, Sprints 9 to 11: engine in the backend, departures, advice, rollout, output contract | 2026-11-16 to 2026-12-06 | 2026-10-05 and 2026-10-07 | `US-051` to `US-054` and `US-071`, `US-072`, `US-074`, `US-075` Done. `US-055`, `US-070`, `US-073` pending evidence from the 12-hour replay that ends at 03:00 +07 on 2026-10-09. |
| Plan 3, Sprint 12: frontend recheck against the mockup, rain test environment, core output hygiene | 2026-12-07 to 2026-12-13 | Starts 2026-10-09 | 15 rows, over the size of one week. `US-088` and `US-089` started early. |

Open items:

- **Routing rollout.** `US-055` needs the 9c timing and the engine proof from the replay. The flag
  `TIME_AWARE_ROUTING` stays off until it has evidence. `US-045` needs the replay's 9c runs and an `ST_Value`
  spot check tool.
- **Map default.** Whether the map shows the situation now or the nearest forecast step is open
  ([[map-shows-forecast-not-now]]). Decide it before the route-forecast chart changes.
- **Storage check.** `US-069` needs the user's decision on a weaker pass condition or a longer replay (ADR-012).
- **Prune `flood_road_values`.** No retention exists (`US-086`, Sprint 12).
- **Backend hardening.** `server.py` and `flood_areas.py` have tests against a real PostGIS and passed a
  48-hour soak (`US-034`, Done). The latency of `GET /flood/points` under concurrent taps (`US-014`) is Done.
- **Unbuilt design.** Everything marked "Designed, not built" remains unbuilt: the citizen app beyond the web
  slice, the council dashboard, the multi-role Redis, the alert engines, push dispatch, NCHMF and gauge input,
  and the fast-track triggers. Build any of them against this file's Built and Designed split.
- **Partner API.** Phase 3's sketch assumed the raster tile design. A partner MVT endpoint would extend the
  built vector-tile pipeline (section 4.2).
- **GRASS GIS dependency.** No GRASS-free rewrite is planned. Track it as an operational dependency if the
  postprocessing environment changes.

## 12. Project identification

- **Project name:** FloodNav (t3-digital-twin repository)
- **Primary contact:** Mai Anh (architecture author and maintainer)
- **Date of last update:** 2026-10-08

## 13. Glossary

- **3Di**: Cloud-based hydraulic simulation engine (`api.3di.live`).
- **ADR**: Architecture decision record. A dated Context, Decision, and Consequences entry.
- **Asset event**: An Airflow 3 signal that a task emits on success. `9b_load_depth_raster` emits one for
  `flood_depth_raster_tile`, and `routing_adapter` runs on it.
- **Cold start**: A simulation that starts from the template's initial conditions. The opposite of a hotstart.
- **Contract tables**: The tables and files listed in [[core-output-contract]] that other applications may read.
- **`custom_model`**: GraphHopper's JSON cost-graph document, derived per request from PostGIS to grade road
  segments for flood-aware routing.
- **Dry cycle**: A 15-minute slot where the rain gate finds no interval at the threshold. The run ends as a
  success and skips every later task.
- **Edge depth table**: The file `<run_ts>.bin` that holds the flood depth of every GraphHopper edge at every
  forecast step of one run (section 4.11).
- **GRASS GIS**: Open-source GIS toolkit used for raster-to-polygon vectorization of depth rasters.
- **Graph hash**: A SHA-256 over the GraphHopper graph's nodes, edges, and geometry. A table is valid only for the
  graph with the same hash.
- **Hotstart**: A simulation that starts from a 3Di saved state of the previous run.
- **MVT**: Mapbox Vector Tile (`.pbf`), the format the map tile pipeline serves.
- **NCHMF**: Trung tâm dự báo KTTV Quốc Gia, the Vietnamese National Centre for Hydro-Meteorological
  Forecasting.
- **Pre-closure time**: The forecast depth 1 hour ahead reaching a vehicle type's hard-block threshold. A
  routing-policy safety buffer distinct from the physical hard-block limit.
- **Rain gate**: The check in `0_check_forecast_rain` that decides whether a slot simulates.
- **Replay**: Running the pipeline on a recorded rain event instead of the live forecast (section 4.12).
- **Road piece**: One row of `road_segment`, a stretch of road with a stable `segment_id`.
- **Run (`run_ts`)**: One pipeline run, named by the Vietnam local time of its earliest depth file, in the form
  `YYYYMMDDTHHMMSS`.
- **Saved state**: A 3Di snapshot that the next run attaches as its initial condition.
- **Step**: One output time of a run. A run has 8 steps, 15 minutes apart.
- **Sticky closure**: The routing rule that closes a road for an arrival when any forecast step from the
  departure to the arrival plus the margin reaches the vehicle's limit (ADR-008).
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
