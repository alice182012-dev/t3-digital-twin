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
diagram). Synced with the code at commit `db99bc1` on the branch `modular` on 2026-10-08. Solid, filled
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
    PHOTON["Photon<br/>(place search)"]:::built
    REPLAY["replay.ps1 + rain_replay.py<br/>(recorded rain event)"]:::built
    CITIZEN["Citizen app"]:::designed
    COUNCIL["Council dashboard"]:::designed
    FCM["FCM / APNs"]:::designed
    PARTNER["Ride-hailing partners"]:::designed
  end

  subgraph PIPE["Simulation & postprocessing"]
    AIRFLOW["Airflow DAG flood_mapping_full<br/>flood_mapping_dag.py<br/>(every 15 min, rain gate)"]:::built
    ADAPTER["Airflow DAG routing_adapter<br/>(runs on the 9b asset event)"]:::built
    DEPTH["calculate_depth.py<br/>depth_*.tif series"]:::built
    RASTERLOAD["raster_load.py<br/>(task 9b_load_depth_raster)"]:::built
    METRICS["extract_run.py<br/>(no DAG task)"]:::built
    EDGETABLE["build_edge_depth.py<br/>(task 9c_build_edge_depth_table, US-041)"]:::built
    TILEEXT["flood_extent.py + publish.py<br/>(GRASS raster→polygon,<br/>prune_polygon_rows every publish)"]:::built
  end

  subgraph DATA["Data stores"]
    PG["storage-postgres (PostGIS)<br/>edge_depth, edge_depth_run<br/>flood_extent_polygon (pruned, US-067)<br/>flood_extent_step<br/>flood_depth_raster_tile<br/>graph_edge, graph_edge_export"]:::built
    MINIO["MinIO<br/>flood-extent (.pbf tiles),<br/>initial-wl, manholes-data"]:::built
    EDGEVOL["Docker volume edge-depth-tables<br/>(run.bin files, latest pointer)"]:::built
    TSDB["timescaledb<br/>histogram tables (empty, D-009)"]:::built
    ULS["User Location Store"]:::designed
  end

  subgraph ROUTE["Routing & map"]
    GH["graphhopper<br/>(graphhopper-time-aware:local,<br/>java/time-aware-routing)"]:::built
    BACKEND["floodmap-backend<br/>server.py<br/>(reads as routing_reader)"]:::built
    FRONTEND["flood-routing-frontend<br/>graphhopper-maps"]:::built
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
  PG -->|contract tables| BACKEND
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
volume `edge-depth-tables`. `floodmap-backend` mounts the same volume read-only and sends a
departure to the engine only when `TIME_AWARE_ROUTING` is on. The engine was deployed and tested on the
server on 2026-10-07 (`US-055`). `scripts/routing_proof/rollout.ps1` turns the flag on for the proof and
puts it back off unless run with `-LeaveOn`. At rest on 2026-10-08 the backend reads
`TIME_AWARE_ROUTING=false`, so ordinary live routing is still single-timestep. Whether `-LeaveOn` was
used is unconfirmed. `US-045` (live timing of task 9c) is still open. The decision record for the engine is
ADR-008 in the architecture document.

TimescaleDB moved from Designed to Built on 2026-10-05 ([[US-066-netcdf-values-storage-redesign|netcdf-values-storage-redesign]],
`US-066`), with a `netcdf_values` hypertable that task `3b_upload_netcdf_postgres` filled. On 2026-10-10 the ingest was retired ([[US-095-retire-the-netcdf-values-ingest|US-095]], D-018, D-022): the task, its scripts, and the tables `netcdf_values`, `netcdf_variable_catalog`, and `mesh_elements` are gone, and so are the three `storage-postgres` netcdf tables. `timescaledb` keeps only the three empty histogram tables. `flood_extent_polygon` on
`storage-postgres` also got an automated prune the same week ([[US-067-prune-flood-extent-polygon-rows|prune-flood-extent-polygon-rows]],
`US-067`), the other table the same incident found growing unbounded.
