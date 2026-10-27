---
date: 2026-10-27
type: concept
status: active
tags: [reference, services, endpoints]
related: ["[[graphhopper-backend]]", "[[routing-depth-threshold-model]]", "[[run-and-test-the-system]]"]
last_updated: 2026-10-27
---

# System reference

This page lists the technology, routing profiles, backend endpoints, services, and folders of the repository. The [README](../../../README.md) gives the overview.

## Tech stack

| Component                    | Technology                                                                | Version pinned in the repository                                                                                                             |
| ---------------------------- | ------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Pipeline orchestration       | Apache Airflow with the Celery executor                                   | `apache/airflow:3.1.7`, Python 3.12 constraints (`Dockerfile`)                                                                           |
| Airflow metadata and broker  | PostgreSQL and Redis                                                      | `postgres:16`, `redis:7.2-bookworm`                                                                                                      |
| Flood simulation             | 3Di API through `threedi-api-client`                                    | `threedi-api-client==5.0.5` (`requirements.txt`)                                                                                         |
| Rain forecast                | Tomorrow.io timelines API                                                 | None                                                                                                                                         |
| Depth calculation            | `threedidepth`                                                          | Not pinned                                                                                                                                   |
| Raster and vector processing | GDAL, rasterio, GRASS GIS                                                 | GDAL 3.6.2, `rasterio==1.4.4`, `numpy==1.26.4`, GRASS from Debian `grass-core`                                                         |
| Flood and road data          | PostgreSQL 17 with PostGIS 3.5                                            | `imresamu/postgis:17-3.5` (service `storage-postgres`)                                                                                   |
| Time-series store            | TimescaleDB                                                               | `timescale/timescaledb:2.30.1-pg17`                                                                                                        |
| Object storage               | MinIO and the `mc` client                                               | `quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z`, `quay.io/minio/mc:RELEASE.2025-08-13T08-35-41Z`                                      |
| Routing engine               | GraphHopper 12.0-SNAPSHOT                                                 | `israelhikingmap/graphhopper@sha256:3e79eb33...` (full digest in `compose.yml`)                                                          |
| Flood routing backend        | Python standard library HTTP server and `psycopg2-binary`               | `python:3.12-slim`                                                                                                                         |
| Place search                 | Photon geocoder                                                           | `PHOTON_BASE_URL`, default `https://photon.komoot.io`                                                                                    |
| Flood routing frontend       | graphhopper-maps fork with React, TypeScript, MapLibre GL, and OpenLayers | `react 19.2.8`, `typescript 5.9.3`, `maplibre-gl 5.16.0`, `ol 10.10.0`, built on `node:22-alpine`, served by `nginx:1.27-alpine` |
| Storage UI backend           | Django, Django REST Framework, Simple JWT, gunicorn                       | `Django>=5.2,<6.0` on `python:3.14-slim`                                                                                                 |
| Storage UI frontend          | React and Vite                                                            | `react ^19.0.0`, `vite ^7.0.0`, built on `node:25-alpine`, served by `nginx:1.29-alpine`                                             |

## Routing profiles and flood limits

`floodmap/graphhopper-flood-road/scripts/flood_utils.py` sets each vehicle's flood limit in
`VEHICLE_PROFILES`. A road piece at or above the limit is closed to that vehicle.

| Profile       | Flood limit | Custom model file     | Listed in the frontend |
| ------------- | ----------- | --------------------- | ---------------------- |
| `motorbike` | 20 cm       | `motorbike.json`    | Yes                    |
| `car`       | 30 cm       | `car_custom.json`   | Yes                    |
| `truck`     | 35 cm       | `truck_custom.json` | No                     |
| `foot`      | 40 cm       | `foot_custom.json`  | Yes                    |

GraphHopper serves all four profiles. `floodmap/graphhopper-maps/config-local.js.example` lists
`motorbike`, `car`, and `foot` only.

## floodmap-backend endpoints

| Method   | Path                    | What it returns                                                                               |
| -------- | ----------------------- | --------------------------------------------------------------------------------------------- |
| `GET`  | `/health`             | Backend status, plus GraphHopper and PostGIS reachability                                     |
| `GET`  | `/info`, `/nearest` | GraphHopper's own response, passed through unchanged                                          |
| `GET`  | `/flood/runs`         | Every `run_ts` in `flood_extent_polygon`, newest first                                    |
| `GET`  | `/flood/timesteps`    | The timesteps of one run (`run`, default `latest`), in Vietnam local time                 |
| `GET`  | `/flood/areas`        | Flood polygons for `valid_time` and `vehicle_type`, the same ones `POST /route` avoids  |
| `GET`  | `/flood/points`       | Depth at `lat` and `lon` for `valid_time`, with status `wet`, `dry`, or `no_data` |
| `POST` | `/flood/forecast`     | Mean depth, maximum depth, and wet fraction along a route per 15-minute step                  |
| `POST` | `/route`              | A GraphHopper route that avoids flooded roads for the given `valid_time` and vehicle        |
| `GET`  | `/places/search`      | Place search results from Photon                                                              |
| `GET`  | `/geocode`            | Photon results in the shape graphhopper-maps expects from a geocoder                          |

## Services and ports

| Service                                                              | Default host port                              | Role                                                                                    |
| -------------------------------------------------------------------- | ---------------------------------------------- | --------------------------------------------------------------------------------------- |
| `flood-routing-frontend`                                           | 8082                                           | Flood map and routing UI                                                                |
| `floodmap-backend`                                                 | 8010                                           | Flood routing and depth API                                                             |
| `graphhopper`                                                      | 8989                                           | Routing engine                                                                          |
| `airflow-apiserver`                                                | 8080                                           | Airflow UI and API                                                                      |
| `airflow-scheduler`, `airflow-dag-processor`, `airflow-worker` | None                                           | Airflow scheduler, DAG parser, and Celery worker                                        |
| `airflow-init`                                                     | None                                           | Migrates the Airflow database and creates the admin user, then exits                    |
| `airflow-trigger-flood-mapping`                                    | None                                           | Unpauses `flood_mapping_full`, then exits                                             |
| `airflow-postgres`, `airflow-redis`                              | None                                           | Airflow metadata database and Celery broker                                             |
| `storage-postgres`                                                 | 5432 on `127.0.0.1`                          | PostGIS for all flood and road tables, and the storage UI's tables                      |
| `timescaledb`                                                      | 5434 on `127.0.0.1`                          | TimescaleDB, schema defined but not loaded                                              |
| `minio`                                                            | 9000 (API) and 9001 (console) on `127.0.0.1` | Object storage                                                                          |
| `minio-init`                                                       | None                                           | Creates the `initial-wl`, `manholes-data`, and `flood-extent` buckets, then exits |
| `storage-backend`                                                  | 8000                                           | Storage UI API                                                                          |
| `storage-frontend`                                                 | 5173                                           | Storage UI                                                                              |

Each port has an override variable in `compose.yml`, such as `FLOOD_ROUTING_FRONTEND_PORT` or
`POSTGRES_HOST_PORT`.

## Repository layout

- `dags/` holds the Airflow DAGs. `flood_mapping_dag.py` defines `flood_mapping_full`, and
  `routing_adapter_dag.py` defines `routing_adapter`, and `flood_tiles_dag.py` defines `flood_tiles`.
  `core_assets.py` defines the assets that link them, and `core_paths.py` the folders they share.
- `scripts/` holds the Python code that the DAG tasks call. It has the 3Di client and simulation
  steps at its top level. Its subfolders are `database/` for table creation, `flood_extent/` for
  tiles and raster loading, `edge_depth/`, `flood_metrics/`, `initial_wl/`, and
  `manholes/`.
- `test/` holds `unittest` tests for the DAG graphs, the rain gate, the depth calculation, 3Di
  calls, and MinIO bucket routing.
- `floodmap/graphhopper-flood-road/` holds the routing side. It has the backend in `backend/`,
  the GraphHopper config and custom models in `graphhopper/`, and the vehicle limits in
  `scripts/flood_utils.py`.
- `floodmap/graphhopper-maps/` holds the frontend fork, its `Dockerfile`, and `nginx.conf`.
- `minio_custom/` holds the storage UI, with `backend/` for Django and `frontend/` for React.
- `artifacts/` is the Obsidian vault with logs, plans, concept pages, blockers, and user stories.
- `marie-curie/` is scratch space for experiments. Git tracks only its `README.md`.
- `compose.yml` defines every service. `Dockerfile` and `requirements.txt` build the Airflow image.

`compose.yml` also bind-mounts `./data` into Airflow. That folder is not in git. It holds the model
inputs in `data/mapping/inputs/` and the working files of each run.
