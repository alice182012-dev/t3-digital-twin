---
date: 2026-09-23
type: concept
status: active
tags: [architecture, diagram]
related: ["[[T3-Digital-Twin_Architecture]]", "[[minio-flood-extent-pipeline]]", "[[graphhopper-backend]]", "[[raster-first-flood-pipeline]]", "[[decision-log]]", "[[US-066-netcdf-values-storage-redesign|netcdf-values-storage-redesign]]", "[[US-067-prune-flood-extent-polygon-rows|prune-flood-extent-polygon-rows]]", "[[BL-022-docker-data-vhdx-fills-c-drive-again|docker-data-vhdx-fills-c-drive-again]]", "[[core-output-contract]]", "[[edge-depth-table-format]]", "[[rain-replay-test-environment]]"]
last_updated: 2026-10-13
---
# Block diagram: T3-Digital-Twin architecture

Companion diagram for `artifacts/raw/T3-Digital-Twin_Architecture.md`, section 3 (Container
diagram). Synced with the code on the branch `modular` on 2026-10-13, after [[US-123-delete-flood-on-roads-and-flood-road-values|US-123]] and [[US-140-delete-the-postgis-input-of-the-flood-tile-build|US-140]]. Solid, filled
boxes are Built. Dashed, grey boxes are Designed, not built. Dotted arrows lead into or between
components that are not built. The box `extract_run.py` is Built, not scheduled: no DAG task calls it.

```mermaid
flowchart TB
  subgraph EXT["External actors & systems"]
    HE["Hydraulic engineer<br/>(manual setup)"]:::built
    ThreeDI["3Di API"]:::built
    TOMORROW["Tomorrow.io<br/>(rain forecast)"]:::built
    NCHMF["NCHMF<br/>(rainfall forecast)"]:::designed
    GAUGE["Gauge network APIs<br/>(hot start)"]:::designed
    DRAINAGE["thoatnuochanoi.vn<br/>(scraped by manholes_dag.py)"]:::built
    PHOTON["Photon, public instance<br/>(place search, slow: BL-021)"]:::built
    REPLAY["replay.ps1 + rain_replay.py<br/>(recorded rain event)"]:::built
    CITIZEN["Citizen app"]:::designed
    COUNCIL["Council dashboard"]:::designed
    FCM["FCM / APNs"]:::designed
    PARTNER["Ride-hailing partners"]:::designed
  end

  subgraph PIPE["Simulation & postprocessing"]
    AIRFLOW["Airflow DAG flood_mapping_full<br/>flood_mapping_dag.py<br/>(every 15 min, rain gate,<br/>standing flood, stale-run guard)"]:::built
    ADAPTER["Airflow DAG routing_adapter<br/>(one task, 9c, on the 9b asset event)"]:::built
    FLOODHIST["Airflow DAG flood_history<br/>load_run.py<br/>(runs on the asset edge_depth)"]:::built
    DEPTH["calculate_depth.py<br/>depth_*.tif series"]:::built
    RASTERLOAD["raster_load.py<br/>(task 9b_load_depth_raster)"]:::built
    METRICS["extract_run.py<br/>(no DAG task)"]:::built
    EDGETABLE["build_edge_depth.py<br/>(task 9c_build_edge_depth_table, US-041)"]:::built
    TILEEXT["flood_extent.py + publish.py<br/>(GRASS raster→polygon,<br/>prune_polygon_rows every publish)"]:::built
  end

  subgraph DATA["Data stores"]
    PG["storage-postgres (PostGIS)<br/>edge_depth, edge_depth_run<br/>flood_depth_raster_tile<br/>flood_extent_polygon (pruned, US-067), flood_extent_step<br/>flood_run_output, forecast_mode, demo_pin<br/>flood_segment_metrics<br/>graph_edge, graph_edge_export"]:::built
    MINIO["MinIO<br/>flood-extent (.pbf tiles),<br/>initial-wl, manholes-data"]:::built
    EDGEVOL["Docker volume edge-depth-tables<br/>(run.bin files, latest pointer)"]:::built
    TSDB["timescaledb<br/>depth_history, history_moment<br/>(written by flood_history, US-106)"]:::built
    ULS["User Location Store"]:::designed
  end

  subgraph ROUTE["Routing & map"]
    GH["graphhopper<br/>(graphhopper-time-aware:local,<br/>java/time-aware-routing)"]:::built
    BACKEND["floodmap-backend<br/>server.py<br/>(reads as routing_reader,<br/>modes LIVE, PENDING, DEMO)"]:::built
    FRONTEND["flood-routing-frontend<br/>graphhopper-maps"]:::built
  end

  subgraph ANALYSISSG["Industry analysis"]
    ANALYSIS["analysis service<br/>(own container and roles,<br/>schema analysis, US-109)"]:::built
  end

  subgraph STORAGEUI["Storage UI"]
    SBACK["storage-backend<br/>(Django/JWT)"]:::built
    SFRONT["storage-frontend<br/>(Vite/React)"]:::built
  end

  ThreeDI -->|results .nc| AIRFLOW
  TOMORROW -->|rain forecast| AIRFLOW
  REPLAY -.->|replaces the forecast in a replay| AIRFLOW
  NCHMF -.->|not implemented| AIRFLOW
  GAUGE -.->|not implemented| AIRFLOW
  DRAINAGE --> MINIO
  PHOTON --> BACKEND
  HE -.->|model, templates| ThreeDI
  AIRFLOW --> DEPTH
  RASTERLOAD -->|asset event, run_ts| ADAPTER
  ADAPTER --> EDGETABLE
  EDGETABLE -->|"asset edge_depth, run_ts"| FLOODHIST
  PG -->|"edge_depth, edge_depth_run"| FLOODHIST
  FLOODHIST -->|"depth_history, history_moment"| TSDB
  AIRFLOW -->|forecast_mode rows| PG
  DEPTH --> RASTERLOAD
  RASTERLOAD -->|flood_depth_raster_tile| PG
  DEPTH --> TILEEXT
  EDGETABLE -->|edge_depth rows| PG
  PG -->|tiles, graph_edge| EDGETABLE
  EDGETABLE -->|"run.bin, edge depth table"| EDGEVOL
  EDGEVOL -->|read-only| GH
  EDGEVOL -->|read-only| BACKEND
  PG -->|edge_depth| METRICS
  TILEEXT -->|flood_extent_polygon| PG
  TILEEXT -->|.pbf tiles| MINIO
  PG -->|"contract tables, forecast_mode, demo_pin"| BACKEND
  PG -->|analysis_reader| ANALYSIS
  TSDB -->|analysis_timescale_reader| ANALYSIS
  BACKEND -->|custom_model, or td_departure| GH
  GH --> BACKEND
  BACKEND --> FRONTEND
  MINIO -->|tiles via nginx| FRONTEND
  SBACK --> PG
  SFRONT --> SBACK

  BACKEND -.->|not implemented| CITIZEN
  BACKEND -.->|not implemented| COUNCIL
  TSDB -.-> CITIZEN
  ULS -.-> CITIZEN
  CITIZEN -.-> FCM
  PARTNER -.-> BACKEND

  classDef built fill:#dff5e1,stroke:#2f9e44,stroke-width:1px;
  classDef designed fill:#f1f3f5,stroke:#adb5bd,stroke-width:1px,stroke-dasharray: 4 3;
```

The per-piece sampler, the task `flood_on_roads` and its table `flood_road_values`, ran from 2026-09-25 until
[[US-123-delete-flood-on-roads-and-flood-road-values|US-123]] deleted it on 2026-10-13 ([[decision-log|D-038]]).
The task `9c_build_edge_depth_table` of the DAG `routing_adapter` now writes the edge depth file and the `edge_depth` rows,
and it runs on the asset event of `9b_load_depth_raster`. `floodmap-backend` reads `edge_depth` and `graph_edge` for the
map overlay and the route fallback, and the engine reads the files. The plan was [[raster-first-flood-pipeline]].

The `graphhopper` service builds from `java/time-aware-routing` and reads the edge depth files from the
volume `edge-depth-tables`. `floodmap-backend` mounts the same volume read-only and sends a departure to the engine
when `TIME_AWARE_ROUTING` is on. The flag is on since 2026-10-12 ([[decision-log|D-034]]). In `DEMO` mode the route skips
the engine and reads the pinned step through the flood areas ([[decision-log|D-043]]). Task `9c` took 24 s on the real runs
of 2026-10-13, and a run took 148 s from `3_calculate_depth` to the end of the chain ([[US-045-prove-the-table-on-the-server|US-045]],
[[US-123-delete-flood-on-roads-and-flood-road-values|US-123]]). The decision record for the engine is ADR-008 in the architecture document.

`flood_mapping_full` writes one row of `forecast_mode` for each slot (`LIVE`, `PENDING`, or `DEMO`), and `demo_pin` holds the
one step of the stored storm that `DEMO` shows. `GET /flood/mode` answers the mode, and in `DEMO` the point read, the flood areas,
and the route use the pinned run ([[US-111-show-a-pinned-demo-flood-when-no-rain-is-forecast|US-111]], [[US-129-pin-the-peak-step-of-the-demo-flood|US-129]],
[[US-130-serve-the-forecast-mode-and-read-the-pinned-step|US-130]], [[decision-log|D-030]]). The DAG skips a run whose slot is older than
two hours, so an unpause cannot revive old work ([[US-139-skip-a-flood-run-whose-slot-is-hours-old|US-139]]).

The DAG `flood_history` copies each run from `edge_depth` into the TimescaleDB tables `depth_history` and `history_moment`, and the
`analysis` service reads both databases through its own read-only roles and writes only its schema `analysis`
([[timescaledb-schema]], [[analysis-service]]). The pipeline tables stay in schema `public` ([[decision-log|D-049]]).

TimescaleDB moved from Designed to Built on 2026-10-05 ([[US-066-netcdf-values-storage-redesign|netcdf-values-storage-redesign]],
`US-066`), with a `netcdf_values` hypertable that task `3b_upload_netcdf_postgres` filled. On 2026-10-10 the ingest was retired ([[US-095-retire-the-netcdf-values-ingest|US-095]], D-018, D-022): the task, its scripts, and the tables `netcdf_values`, `netcdf_variable_catalog`, and `mesh_elements` are gone, and so are the three `storage-postgres` netcdf tables. `timescaledb` holds four tables: `depth_history` and `history_moment`, which the DAG `flood_history` fills, and `institution_histogram_bar` and `background_forecast_depth`, which stay empty (D-009). `flood_extent_polygon` on
`storage-postgres` also got an automated prune the same week ([[US-067-prune-flood-extent-polygon-rows|prune-flood-extent-polygon-rows]],
`US-067`), the other table the same incident found growing unbounded.
