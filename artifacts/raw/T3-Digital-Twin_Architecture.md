---
date: 2026-09-23
type: concept
status: active
tags: [architecture, source-of-truth, floodnav]
related: ["[[T3-Digital-Twin_Architecture]]", "[[minio-flood-extent-pipeline]]", "[[graphhopper-backend]]", "[[storage-backend-django-layer]]", "[[3di-simulation-orchestration]]", "[[routing-depth-threshold-model]]"]
last_updated: 2026-09-23
---
# FloodNav — Architecture

Working copy of `artifacts/raw/SW Architecture.md`, rewritten into the C4-style template at
`artifacts/raw/ideas/architecture.md-howto/Architecture template.md` (Project Structure → System
Diagram → Core Components → Data Stores → External Integrations → Deployment → Security →
Dev/Testing → ADRs → Roadmap → Glossary), with the two confirmed architecture decisions folded in
directly rather than kept as a separate errata list: map tiles moved from raster PNG to vector
polygons, and routing moved from Valhalla to GraphHopper.

Every component is marked **Built** (running in `compose.yml`, confirmed against code) or
**Designed, not built** (specified in the original whiteboard design, no corresponding service or
code exists in this repository). The original file predates both decisions and describes Valhalla
and raster tiles as current; this rewrite is the version to build against.

## 1. Project Structure

```
t3-digital-twin/
├── dags/                        # Airflow DAGs (constant_cycle + background_cycle orchestration)
│   └── flood_mapping_dag.py     # Main pipeline: simulate → depth calc → geojson → tiles
├── scripts/                     # Python pipeline code, run by Airflow tasks
│   ├── calculate_depth.py       # threedidepth → depth_YYYYMMDD_HHMMSS.tif series
│   ├── extract_geojson.py       # depth.tif → per-segment sampling → flood_road_values (routing)
│   ├── mapping/                 # extract_geojson_full.py, merge_geojson.py
│   ├── flood_extent/            # flood_extent.py (GRASS raster→polygon), publish.py (MinIO/PostGIS)
│   ├── initial_wl/, manholes/, database/
│   └── threedi_client.py        # 3Di API orchestration (connect, upload, start, download)
├── floodmap/
│   ├── graphhopper-flood-road/  # Active routing stack: backend/ (server.py), scripts/, graphhopper/
│   ├── graphhopper-maps/        # Active frontend: vendored GraphHopper Maps fork, nginx.conf
│   └── valhalla-flood-road-test/ # Retired PoC (ADR-002); left on disk, not run by compose.yml
├── minio_custom/                # storage-backend (Django/JWT/boto3) + storage-frontend (Vite/React)
├── test/                        # Pytest suite
├── einstein/                    # Disposable scratch space
├── artifacts/                   # This Obsidian vault
└── compose.yml                  # Full service definition; runs on the remote Docker host only
```

## 2. System Context

**FloodNav** is a real-time flood navigation and warning platform for Hanoi: a continuous
hydrodynamic simulation pipeline producing flood depth maps, vehicle-aware routing, forecast
histograms, and push alerts, refreshed roughly every 30 minutes by design.

### Actors and external systems

| Actor / system                               | Relationship                                                                                                                                                             | Status                                                                                   |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------- |
| Hydraulic engineer                           | Builds the 3Di schematisation, calculation-node mapping, and simulation templates (one-time manual setup, versioned in a geopackage)                                     | Built (manual, outside the automated pipeline)                                           |
| 3Di (`api.3di.live`)                       | Cloud hydraulic simulation engine; FloodNav submits jobs, uploads rainfall and water-level boundary conditions, downloads`results_3di.nc` after each run               | Built — see[[3di-simulation-orchestration]]                                                                             |
| Trung tâm dự báo KTTV Quốc Gia (NCHMF)   | Rainfall forecast (GRIB2/NetCDF), polled once per cycle as the rainfall boundary condition                                                                               | Built                                                                                    |
| Gauge network APIs                           | Real-time water-level sensors; read at cycle start to hot-start the simulation from observed conditions                                                                  | Built                                                                                    |
| Citizen (mobile/web app)                     | Views flood map, plans route, receives alerts                                                                                                                            | Designed, not built — no citizen app exists in this repository                          |
| City council (dashboard)                     | Monitors city flood status, dispatches response, logs decisions                                                                                                          | Designed, not built                                                                      |
| Ride-hailing services (GrabBike, XanhSM, Be) | Consume flood data programmatically for fleet routing (Phase 3 partner API)                                                                                              | Designed, not built, and its own extension point (a partner MVT endpoint) is unbuilt too |
| FCM / APNs                                   | Push alert delivery — a one-way, asynchronous channel FloodNav has no delivery visibility into, flagged in the original design as a reliability risk needing a fallback | Designed, not built — no alert engine exists to call it                                 |

### Design rationale carried forward

- **Users are segmented by decision type, not just by role.** Citizens make immediate personal
  safety decisions (travel or not, which route, stay or go). The council coordinates
  city-wide operational response (dispatch, public announcements, service-accessibility calls).
  Ride-hailing partners consume a data feed programmatically; they were never meant to use a
  FloodNav UI.
- **Community reports are isolated from the simulation model by design**, not as an oversight: live
  citizen feedback must not be able to contaminate the hydrodynamic results emergency decisions are
  based on. Its primary long-term value is post-event model calibration, once verified separately.
- **FCM/APNs is modeled as an external system FloodNav calls, not a channel FloodNav owns**, because
  the alert-delivery contract is one-way with no delivery guarantee. This is why the design requires
  an in-app poller as a fallback (see §4.5) rather than relying on push delivery alone for
  safety-critical alerts.
- **A 15-minute fast-track mode** is specified for the simulation cadence: triggered by gauge rise
  > 5 cm in 15 minutes, an NCHMF forecast >70 mm/hr within 2 hours, 3 or more community flood reports
  > in 30 minutes, or manual operator override; it auto-reverts to the default cadence after two
  > consecutive calm cycles. Designed, not built.
  >

## 3. Container diagram

| Container                                                                    | Tech                                              | Status              | Responsibility                                                                                                                                                              |
| ---------------------------------------------------------------------------- | ------------------------------------------------- | ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Airflow (webserver, scheduler, dag-processor, worker, trigger-flood-mapping) | Apache Airflow                                    | Built               | Orchestrates`flood_mapping_dag.py`: simulation trigger, depth calc, geojson extraction, tile build                                                                        |
| `graphhopper`                                                              | Pinned GraphHopper image, digest-pinned (see §6) | Built               | Flood-weighted routing engine — replaces the Valhalla design (ADR-002, §10)                                                                                               |
| `floodmap-backend` (`graphhopper-flood-road/backend/server.py`)          | FastAPI/Python                                    | Built               | Derives GraphHopper's`custom_model` from PostGIS, proxies GraphHopper, serves `/flood/*`                                                                                |
| `flood-routing-frontend` (`graphhopper-maps`)                            | TypeScript, vendored GraphHopper Maps fork        | Built               | Map + routing UI; renders vector`.pbf` tiles, sends route requests                                                                                                        |
| `minio` + `minio-init`                                                   | MinIO (S3-compatible)                             | Built               | `flood-results-full`, `initial-wl`, `manholes-data`, `flood-extent` buckets — replaces the S3 + CloudFront design (ADR-001, §10)                                  |
| `storage-postgres`                                                         | PostgreSQL + PostGIS                              | Built               | `flood_road_values`, `flood_extent_polygon`, and `minio_custom`'s role/access tables                                                                                  |
| `storage-backend` + `storage-frontend` (`minio_custom/`)               | Django REST + Vite/React                          | Built               | Human-operator UI over raw MinIO buckets — separate from the pipeline's own automated bucket use; see[[storage-backend-django-layer]]                                                                      |
| `airflow-postgres`, `airflow-redis`                                      | PostgreSQL, Redis                                 | Built               | Airflow's own metadata DB and Celery broker —**not** the multi-role (task queue / pub-sub / cache) Redis described below                                             |
| Redis (task queue, pub-sub bus, short-TTL cache)                             | Redis                                             | Designed, not built | Fans out postprocessing work, publishes cycle-completion events, caches API responses                                                                                       |
| TimescaleDB                                                                  | —                                                | Designed, not built | Institution histograms, background_cycle forecast series, depth history                                                                                                     |
| Citizen-facing REST API (as a container distinct from`floodmap-backend`)   | —                                                | Designed, not built | `floodmap-backend` covers routing and map-tile listing only; alerts, community reports, and forecast endpoints from the original design don't exist as endpoints anywhere |
| User Location Store                                                          | —                                                | Designed, not built | User GPS + consent mode                                                                                                                                                     |
| Mobile/web app, City council dashboard                                       | —                                                | Designed, not built | See §4.5–4.6                                                                                                                                                              |

**Key data flows (built):** Gauge network APIs and NCHMF feed the simulation pipeline over HTTPS →
`calculate_depth.py` produces `depth_*.tif` → `extract_geojson.py` writes `flood_road_values`
(routing) and `flood_extent.py`/`publish.py` write `flood_extent_polygon` + MinIO `.pbf` tiles
(map) in parallel, independent branches → `floodmap-backend` reads both PostGIS tables to serve
GraphHopper-graded routes and the map's timestep/tile listing → `flood-routing-frontend` fetches
tiles from MinIO (via nginx) and requests routes from `floodmap-backend`.

### Block diagram: 
[[architecture-block-diagram]] 
## 4. Core components

### 4.1 Simulation pipeline (Built)

Two Airflow-orchestrated cycles, unchanged from the original design:

- **constant_cycle** (6 h duration, 15-min timestep, 25 GeoTIFFs per run): runs continuously, next
  cycle starting immediately after the previous completes, budgeted to finish within 30 minutes.
  Rainfall ingestion polls NCHMF and projects the forecast onto the 3Di mesh via a fixed spatial
  mapping. Gauge ingestion hot-starts each cycle from observed water levels
  (`initial_waterlevels.csv`: 3Di calculation-node ID, observed level in metres; a failed gauge
  reading falls back to the previous cycle's value).
- **background_cycle** (24 h duration, 60-min timestep, 25 GeoTIFFs per run): a separate DAG on a
  fixed 3-hour schedule, budgeted 30–60 minutes, does not block or interfere with constant_cycle.

Both converge on the same 3Di API orchestration sequence: connect (personal API token) → create a
simulation from the per-cycle template → upload `initial_waterlevels.csv` and poll until valid
(max 900 × 1 s retries) → assign it to the simulation, clearing any prior assignment first → upload
`rain.nc` and poll until processed → start the simulation → download `results_3di.nc` and
`gridadmin.h5`. See [[3di-simulation-orchestration]] for the full sequence and code references.

One-time manual setup (outside the automated pipeline, updated only on model rebuild): the 3Di
model itself (versioned geopackage, from 1–2 m LiDAR DTM, building footprints, drainage network,
Manning's n), the calculation-node mapping (gauge station → 3Di node ID, static CSV), the rainfall
spatial mapping (NCHMF grid cell → mesh cell, fixed NetCDF raster lookup), and the two simulation
templates.

### 4.2 Depth calculation and its two independent consumers (Built)

`scripts/calculate_depth.py` runs `threedidepth.calculate_waterdepth()` per timestep, producing 25
`depth_YYYYMMDD_HHMMSS.tif` files per cycle (filenames in Vietnam local time, converted to UTC
downstream — see §4.4). This is the one artifact both of the following pipelines read; they share
only this input and neither reads the other's output.

| Consumer                                                                                | Reads for                              | Writes to                                                                                                                            | Serves                                                                                    |
| --------------------------------------------------------------------------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------- |
| `scripts/extract_geojson.py` / `scripts/mapping/*`                                  | Per-segment road depth sampling        | PostGIS`flood_road_values` (keyed `timestamp, forecast_time`)                                                                    | GraphHopper routing (`flood_areas.derive_areas`, `POST /route`, `GET /flood/areas`) |
| `scripts/flood_extent/flood_extent.py` (GRASS GIS raster→polygon) via `publish.py` | Full-extent flood polygon per timestep | PostGIS`flood_extent_polygon` (keyed `run_ts, valid_time_utc`) + MinIO `flood-extent/runs/<run_ts>/<timestep>/{z}/{x}/{y}.pbf` | Map overlay (`GET /flood/runs`, `GET /flood/timesteps`)                               |

`dags/flood_mapping_dag.py` task 9 (`9_build_flood_tiles`) runs the polygon pipeline after tasks 3
(`calculate_depth`) and 5 (`merge_geojson`), without blocking the road-mapping chain that writes
`flood_road_values`. Routing and map display run on different cadences and pipelines by design; this
is not an incomplete migration. See [[minio-flood-extent-pipeline]].

### 4.3 Filename-to-UTC conversion (Built)

`calculate_depth.py` writes filenames in Vietnam local time (UTC+7). `publish.py`'s
`valid_time_utc()` converts that to UTC before writing `flood_extent_polygon.valid_time_utc`;
`flood_extent_runs.py`'s `list_timesteps` converts back to local time for `GET /flood/timesteps`,
because MinIO's on-disk folder names stay keyed by the original local-time string. Getting either
conversion direction wrong makes `GET /flood/timesteps` return a time matching no tile the frontend
can fetch — off by exactly 7 hours.

### 4.4 Postprocessing workers from the original design (Designed, not built)

The original whiteboard design specifies a metric extractor and four Tier 1 / two Tier 2 workers,
none of which exist as code in this repository:

- **Flood metric extractor**: time-to-peak, recession onset, per-vehicle passability restoration
  time, T+1h/T+2h forecast depth, and pre-closure time per segment per vehicle type (the forecast
  depth 1 hour ahead reaching the hard-block threshold — a routing-policy safety buffer sitting on
  top of the physical hard-block limit, distinct from it).
- **Tier 1** (parallel, no inter-worker dependency): tile generator, segment extractor, institution
  histogram builder, user alert engine.
- **Tier 2** (depends on the segment extractor completing): segment alert engine, district
  aggregator.

The two pipelines that are actually built (§4.2) cover only a subset of this: routing-grade
per-segment depth (roughly the segment extractor's job, without the pre-closure-flag and alert
machinery around it) and the full-extent polygon (a new capability the original tile generator
didn't have — see ADR-001, §10).

### 4.5 Flood Routing Engine (Built, on GraphHopper)

The original design marked this component a black box on the whiteboard and named Valhalla as the
implementation. The built system replaced Valhalla with a pinned GraphHopper instance, fronted by a
custom backend (ADR-002, §10; full detail in [[graphhopper-backend]]):

- `graphhopper` runs a digest-pinned image
  (`israelhikingmap/graphhopper@sha256:3e79eb33862028cfc58f9d6c162630b68638d6aad790b5a698c854dbbaa7fe32`),
  not `:latest`, because the `ch.disable`-in-body flood-graded routing behavior this system depends
  on is undocumented and could change without notice.
- `floodmap-backend`'s `server.py` derives a `custom_model` (GraphHopper's cost-graph document) from
  PostGIS `flood_road_values` via `flood_areas.derive_areas`, and forwards the graded request to
  GraphHopper. `GET /flood/areas` (map overlay) and `POST /route` (routing) call the same derivation
  function, so the overlay a user sees and the area GraphHopper actually routes around can't drift
  apart. Pre-closure segments are treated as cost = infinity, as the original design specified.
- Vehicle thresholds (`graphhopper-flood-road/scripts/flood_utils.py`'s `VEHICLE_PROFILES`):
  motorbike 20 cm, car 30 cm, truck 35 cm, foot 40 cm. All four vehicle profiles are live in
  GraphHopper's `config.yml` and confirmed selectable in the deployed frontend as of 2026-09-23.
- `floodmap/valhalla-flood-road-test/` (the prior implementation and its own compose file, backend,
  frontend, and `flood_utils.py`) is retired but left on disk, untouched, for reference; it is not
  run by `compose.yml`.

### 4.6 REST API / backend (Built subset + Designed subset)

**Built**, served by `floodmap-backend`:

| Path                             | Method | Purpose                                                                    |
| -------------------------------- | ------ | -------------------------------------------------------------------------- |
| `/health`                      | GET    | Backend, GraphHopper, and PostGIS health in one payload                    |
| `/info`, `/nearest`          | GET    | Proxied to GraphHopper unchanged                                           |
| `/flood/runs`                  | GET    | Distinct`run_ts` values from `flood_extent_polygon`                    |
| `/flood/timesteps`             | GET    | Timesteps for one run, converted back to Vietnam local time                |
| `/flood/areas`                 | GET    | The same flood polygons`POST /route` grades against, for the map overlay |
| `/route`                       | POST   | Flood-graded route (see §4.5)                                             |
| `/places/search`, `/geocode` | GET    | Place search, backed by`place_search.py`                                 |

**Designed, not built** (from the original citizen-facing REST API sketch — no corresponding
endpoint exists anywhere in this repository): `GET /flood/tiles/{z}/{x}/{y}` (superseded by the
`/flood/runs` + `/flood/timesteps` + MinIO `.pbf` path above, not a gap — see ADR-001), `GET /flood/points`, `POST /community/report`, `POST /user/location`, `GET /flood/alerts`, `GET /flood/forecast`, `GET /flood/route/forecast`, `GET /places/flood`, and the full city council
dashboard endpoint set (`/dashboard/preclosure`, `/dashboard/institutions/access`,
`/dashboard/dispatch`, `/dashboard/districts/summary`).

### 4.7 Mobile / web app (Designed, not built)

No citizen mobile or web app exists in this repository. The original design specifies: a map view
with layer toggles and vehicle-mode selection; a route planner with per-step depth badges and a
route flood-depth histogram (8 bars, 30-min resolution, 4 h lookahead, computed at query time — see
§4.9); a flood status bottom sheet; an institution place-detail sheet with a 24-hour "popular
times"-style histogram; an alert manager with two modes (an FCM/APNs out-of-app receiver, and an
in-app `/flood/alerts` poller as the primary, delivery-guaranteed channel — see §2's design
rationale on why FCM/APNs is modeled as an external system); and a community reporter (photo, depth
estimate, passability vote per vehicle type; isolated from routing and official depth values;
pins expire after 2 hours unless reconfirmed).

The one client that **is** built, `flood-routing-frontend` (`graphhopper-maps`), covers only the
map + routing slice of this design: it renders `.pbf` vector tiles and issues route requests
against `floodmap-backend`, with no histogram, alert, or community-report functionality.

### 4.8 City council dashboard (Designed, not built)

No dashboard exists in this repository. The original design specifies four layers: situational
awareness (full-city flood heatmap, staleness banner, district summary counts); a pre-closure alert
feed as the primary dispatch trigger (segments in pre-closure state, institution access panel);
a dispatch workflow layer (action panel with duplicate-dispatch prevention, a chronological
deployment log exportable as CSV, an announcement composer producing draft Vietnamese-language text
for manual publishing); and a forecast/planning layer (24-hour district forecast panel with a
timestep scrubber, a peak-and-recession timeline, and a pipeline health monitor reading
`GET /pipeline/status` — itself an undesigned-but-unbuilt endpoint here).

### 4.9 Histogram specifications (Designed, not built)

Two histogram types, both query-pattern-dependent on data the built pipeline does not yet produce:

- **Institution histogram** ("popular times" style): 24 hourly bars, bars 1–6 from constant_cycle
  (refreshed every 30 min), bars 7–24 from background_cycle (refreshed every 3–6 h), served from
  TimescaleDB by `GET /places/flood`.
- **Route histogram** ("traffic on route" style): 8 bars at 30-min resolution over a 4-hour visible
  window (6 hours computed internally for "best departure"), computed at query time by the route
  controller from PostGIS per-segment forecast depths, not pre-computed by any pipeline worker.
  Served by `GET /flood/route/forecast`.

## 5. Data stores

| Store                                                                                      | Type                       | Status              | Holds                                                                                                                   |
| ------------------------------------------------------------------------------------------ | -------------------------- | ------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `storage-postgres`                                                                       | PostgreSQL + PostGIS       | Built               | `flood_road_values` (routing), `flood_extent_polygon` (map audit copy), `minio_custom`'s role/access-group tables |
| MinIO                                                                                      | S3-compatible object store | Built               | `flood-results-full`, `initial-wl`, `manholes-data` (private), `flood-extent` (public download, `.pbf` tiles) |
| `airflow-postgres`                                                                       | PostgreSQL                 | Built               | Airflow's own metadata DB                                                                                               |
| `airflow-redis`                                                                          | Redis                      | Built               | Airflow's Celery task broker — not the multi-role Redis below                                                          |
| Redis (task queue / pub-sub / short-TTL cache)                                             | Redis                      | Designed, not built | Postprocessing fan-out, cycle-completion events, API response cache                                                     |
| TimescaleDB                                                                                | —                         | Designed, not built | Institution histograms, background_cycle forecast series, depth history                                                 |
| User Location Store                                                                        | PostgreSQL                 | Designed, not built | User GPS + consent mode, read by the (also undesigned-but-unbuilt) user alert engine                                    |
| PostGIS (extended schema: dispatch log, community reports, district summary, institutions) | PostgreSQL + PostGIS       | Designed, not built | Extends the built`storage-postgres` instance; none of these tables exist yet                                          |

## 6. External integrations

| Service                            | Purpose                                                                                                                                                     | Integration                  | Status                                                                                                                           |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| 3Di (`api.3di.live`)             | Hydraulic simulation                                                                                                                                        | REST API, personal API token | Built                                                                                                                            |
| NCHMF                              | Rainfall forecast (GRIB2/NetCDF)                                                                                                                            | HTTPS poll, once per cycle   | Built                                                                                                                            |
| Gauge network APIs                 | Observed water levels                                                                                                                                       | HTTPS, cycle start           | Built                                                                                                                            |
| FCM / APNs                         | Push alerts                                                                                                                                                 | HTTPS / FCM REST             | Designed, not built                                                                                                              |
| Google Maps                        | Place search, geocoding (citizen app)                                                                                                                       | —                           | Designed, not built                                                                                                              |
| Ride-hailing partner API (Phase 3) | Batch depth queries (`POST /partner/flood/points`), MVT tile serving (`GET /flood/vtiles/{z}/{x}/{y}.mvt`), B2B API keys with per-partner rate limiting | —                           | Designed, not built. Would extend the built vector-tile pipeline (§4.2), not the retired raster one the original sketch assumed |

## 7. Deployment and infrastructure

- **All Docker workloads run on a remote host**, never the local machine. `docker context ls` shows
  a `remote-server` context (`ssh://tecotec@100.67.84.55`); every `docker`/`docker compose` command
  must target it, either via that active context or `--context remote-server` per command.
- Local edits must be pushed and pulled onto the remote host
  (`ssh tecotec@100.67.84.55 "cd C:\Users\TECOTEC\airflow_new && git pull"`, a Windows host over
  OpenSSH, cmd.exe not bash) before `compose.yml`'s bind-mounted services (`./dags`, `./scripts`,
  `./data`, etc.) pick up local changes.
- `graphhopper` is pinned by image digest, not `:latest` (§4.5).
- `storage-backend`/`storage-frontend` and `graphhopper`/`floodmap-backend`/`flood-routing-frontend`
  are two separate stacks sharing one `storage-postgres` instance (default database name
  `minio_custom`).
- The original design's S3 + CloudFront CDN for map tiles does not exist; MinIO behind nginx serves
  that role instead (§10, ADR-001).

## 8. Security considerations

- MinIO: only the `flood-extent` bucket is set to public anonymous download
  (`mc anonymous set download`). The MinIO API port is bound to `127.0.0.1`; public access exists
  only through nginx's proxy, never directly against MinIO.
- `minio_custom/backend` (the storage UI) authenticates with JWT
  (`storage_api/authentication.py`) and has its own role/visibility/access-group model, separate
  from the flood pipeline's own bucket use.
- `graphhopper`'s pinned image digest is itself a stability control: the `ch.disable` behavior the
  routing flow depends on is undocumented in that build and could regress on an unpinned upgrade.
- The original design's citizen-facing auth (community-report tokens, user-location consent tokens,
  council dispatch tokens) has no corresponding implementation — there is no citizen-facing
  authenticated endpoint in this repository today.

## 9. Development and testing environment

- `test/` — pytest suite: 3Di auth, MinIO bucket routing, NetCDF input modeling, rain-gate logic,
  ThreeDI state.
- `einstein/` — disposable experiment scratch space (repo root), not git-tracked except its own
  README; an idea from `artifacts/raw/ideas/` graduates out of here into a real script, DAG, or
  concept page once it works.
- `floodmap/valhalla-flood-road-test/` — retired PoC, kept for reference, not part of the active
  test surface.

## 10. Architecture decision records

### ADR-001: Replace raster PNG tiles with vector polygon tiles for map visualization

**Date:** 2026-09-22 **Status:** Accepted, shipped
**Context:** The original design's Tile generator worker rendered each depth GeoTIFF's colour ramp
to raster PNG tiles (`gdal2tiles`), served from an S3 + CloudFront CDN. A raster tile carries only
colour; it can't expose distinct segment states, per-pixel depth values, or a data audit trail
without a separate lookup.
**Decision:** Dissolve each timestep's depth raster into banded polygons (GRASS GIS, inside
`flood_extent.py`), cut those polygons into Mapbox vector tiles (`.pbf`), and store the same
polygons in PostGIS (`flood_extent_polygon`) as an audit copy. Serve the `.pbf` tiles from MinIO
behind nginx instead of S3 + CloudFront.
**Consequences:** The map overlay is now attribute-bearing vector geometry, not a coloured bitmap.
The storage backend moved from S3 + CloudFront to self-hosted MinIO. The REST surface for map tiles
changed shape (`/flood/runs` + `/flood/timesteps` replace the single `/flood/tiles/{z}/{x}/{y}`
redirect). GRASS GIS is now a hard runtime dependency; no GRASS-free rewrite is planned. Full detail
in [[minio-flood-extent-pipeline]].

### ADR-002: Replace Valhalla with GraphHopper as the flood routing engine

**Date:** commit `6394e27` ("the Valhalla-to-GraphHopper rewrite") **Status:** Accepted, shipped
**Context:** The original design named Valhalla as the Flood Routing Engine's implementation: a
flood-weighted graph re-weighted each cycle, queried by the route controller.
**Decision:** Replace Valhalla with a pinned GraphHopper instance, fronted by a new `server.py`
backend that derives GraphHopper's `custom_model` from PostGIS instead of Valhalla's
`linear_cost_factors`. The prior Valhalla implementation is left on disk untouched, retired but not
deleted.
**Consequences:** `POST /route` and `GET /flood/areas` are served by the GraphHopper-fronting
backend. The Valhalla-era frontend is retired; the active frontend is `graphhopper-maps`. Vehicle
thresholds and flood-cost derivation moved to a trimmed fork of the Valhalla scripts, related by a
straight fork rather than a shared dependency. GraphHopper's `custom_model.areas` and Valhalla's
`linear_cost_factors` are not wire-compatible — the substitution is conceptual, not literal. Full
detail in [[graphhopper-backend]].

## 11. Future considerations / roadmap

- Backend hardening for `floodmap-backend`: `server.py` and `flood_areas.py` postdate the
  Valhalla-to-GraphHopper rewrite with no regression tests and no soak time yet.
- Everything marked "Designed, not built" above — the citizen app, council dashboard, TimescaleDB
  histograms, the multi-role Redis, alert engines, and push notification dispatch — remains
  unbuilt. Building any of it should target this document's Built/Designed split as the current
  state, not assume those containers already exist.
- Phase 3's partner API sketch (batch depth queries, MVT tile serving) assumed the raster tile
  design as its baseline. There is no PNG baseline left; a partner MVT endpoint would extend the
  built vector-tile pipeline (§4.2) instead.
- GRASS GIS dependency in the tile pipeline: no GRASS-free rewrite is planned, but worth tracking as
  an operational dependency if the postprocessing environment ever changes.

## 12. Project identification

- **Project name:** FloodNav (t3-digital-twin repository)
- **Primary contact:** Mai Anh (architecture author and maintainer)
- **Date of last update:** 2026-09-23

## 13. Glossary

- **3Di**: Cloud-based hydraulic simulation engine (`api.3di.live`).
- **ADR**: Architecture decision record — a dated Context/Decision/Consequences entry.
- **GRASS GIS**: Open-source GIS toolkit; used here for raster-to-polygon vectorization of depth
  rasters.
- **MVT**: Mapbox Vector Tile (`.pbf`), the format the map tile pipeline serves.
- **NCHMF**: Trung tâm dự báo KTTV Quốc Gia, the Vietnamese National Centre for Hydro-Meteorological
  Forecasting.
- **Pre-closure time**: the forecast depth 1 hour ahead reaching a vehicle type's hard-block
  threshold — a routing-policy safety buffer distinct from the physical hard-block limit itself.
- **`custom_model`**: GraphHopper's JSON cost-graph document, derived per-request from PostGIS to
  grade road segments for flood-aware routing.

## 14. Revision history and version control

Once this file moves to `artifacts/raw/`, version control is git: `artifacts/` is already tracked in
this repository, so every edit becomes a normal commit and `git log -p` against this file's path is
the full history — no separate versioning scheme is needed. Two habits keep that history legible
without archaeology: keep `last_updated` in the frontmatter current on every edit, and add a dated
bullet below whenever a section changes materially, the same way a blocker page's "Status history"
works.

**History:**

- 2026-09-23 — Rewrote the original `SW Architecture.md` into the C4-style template
  (`architecture.md-howto/Architecture template.md`), folding in ADR-001 (raster → vector tiles) and
  ADR-002 (Valhalla → GraphHopper) directly, and marking every component Built or Designed-not-built
  against `compose.yml`'s actual service list.
