---
date: 2026-09-23
type: concept
status: active
tags: [architecture, diagram]
related: ["[[T3-Digital-Twin_Architecture]]", "[[minio-flood-extent-pipeline]]", "[[graphhopper-backend]]", "[[raster-first-flood-pipeline]]", "[[flood-on-roads]]", "[[road-segment-table]]", "[[decision-log]]", "[[netcdf-values-storage-redesign]]", "[[prune-flood-extent-polygon-rows]]", "[[docker-data-vhdx-fills-c-drive-again]]"]
last_updated: 2026-10-07
---
# Block diagram: T3-Digital-Twin architecture

Companion diagram for `artifacts/raw/T3-Digital-Twin_Architecture.md`, section 3 (Container
diagram). Kept as its own page because `raw/` is read-only source material this page doesn't edit.
Solid, filled boxes are Built; dashed, grey boxes are Designed, not built. Dotted arrows lead into or
between undesigned-but-unbuilt components.

```mermaid
flowchart TB
  subgraph EXT["External actors & systems"]
    HE["Hydraulic engineer<br/>(manual setup)"]
    ThreeDI["3Di API"]
    NCHMF["NCHMF<br/>(rainfall forecast)"]
    GAUGE["Gauge network APIs"]
    CITIZEN["Citizen app"]:::designed
    COUNCIL["Council dashboard"]:::designed
    FCM["FCM / APNs"]:::designed
    PARTNER["Ride-hailing partners"]:::designed
  end

  subgraph PIPE["Simulation & postprocessing"]
    AIRFLOW["Airflow DAG<br/>flood_mapping_dag.py"]:::built
    ADAPTER["Airflow DAG routing_adapter<br/>(runs on the 9b asset event)"]:::built
    DEPTH["calculate_depth.py<br/>depth_*.tif series"]:::built
    NETCDF["netcdf_to_pg.py<br/>(task 3b_upload_netcdf_postgres)"]:::built
    RASTERLOAD["raster_load.py<br/>(task 9b_load_depth_raster)"]:::built
    ROADLOAD["load_road_segments.py<br/>(task load_road_segments)"]:::built
    ROUTEEXT["flood_on_roads.py<br/>(task flood_on_roads)"]:::built
    EDGETABLE["build_edge_depth.py<br/>(task 9c_build_edge_depth_table, US-041)"]:::built
    TILEEXT["flood_extent.py + publish.py<br/>(GRASS raster→polygon,<br/>prune_polygon_rows every publish)"]:::built
  end

  subgraph DATA["Data stores"]
    PG["storage-postgres (PostGIS)<br/>flood_road_values<br/>flood_extent_polygon (pruned, US-067)<br/>flood_depth_raster_tile<br/>road_segment"]:::built
    MINIO["MinIO<br/>flood-extent bucket (.pbf tiles)"]:::built
    TSDB["timescaledb (US-066)<br/>mesh_elements<br/>netcdf_variable_catalog<br/>netcdf_values (compressed, 48h retention)"]:::built
    ULS["User Location Store"]:::designed
  end

  subgraph ROUTE["Routing & map"]
    GH["graphhopper<br/>(pinned image)"]:::built
    BACKEND["floodmap-backend<br/>server.py"]:::built
    FRONTEND["flood-routing-frontend<br/>graphhopper-maps"]:::built
  end

  subgraph STORAGEUI["Storage UI"]
    SBACK["storage-backend<br/>(Django/JWT)"]:::built
    SFRONT["storage-frontend<br/>(Vite/React)"]:::built
  end

  ThreeDI -->|results_3di.nc| AIRFLOW
  NCHMF -->|rainfall forecast| AIRFLOW
  GAUGE -->|water levels| AIRFLOW
  HE -.->|model, templates| ThreeDI
  AIRFLOW --> DEPTH
  AIRFLOW --> NETCDF
  RASTERLOAD -->|asset event, run_ts| ADAPTER
  ADAPTER --> ROADLOAD
  ADAPTER --> ROUTEEXT
  ADAPTER --> EDGETABLE
  NETCDF -->|mesh, variables, values| TSDB
  DEPTH --> RASTERLOAD
  RASTERLOAD -->|flood_depth_raster_tile| PG
  ROADLOAD -->|road_segment| PG
  PG -->|tiles, road pieces| ROUTEEXT
  DEPTH --> TILEEXT
  ROUTEEXT -->|flood_road_values| PG
  PG -->|tiles, graph_edge| EDGETABLE
  EDGETABLE -->|"run.bin, edge depth table"| EDGEFILES["edge_depth folder<br/>(read by US-043)"]:::designed
  TILEEXT -->|flood_extent_polygon| PG
  TILEEXT -->|.pbf tiles| MINIO
  PG --> BACKEND
  BACKEND -->|custom_model| GH
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

The GeoJSON chain that used to write `flood_road_values` (`scripts/mapping/extract_geojson_full.py`
through `scripts/database/geojson_to_pg.py`) left `dags/flood_mapping_dag.py` on 2026-09-24. On
2026-09-25 the DAG task `flood_on_roads` took over as the writer. It reads the run's tiles from
`flood_depth_raster_tile` and the road pieces from `road_segment`. Since 2026-10-07 it runs in the
DAG `routing_adapter`, after `load_road_segments`, on the asset event of `9b_load_depth_raster`
(commit `77169c3` on the branch `modular`, not yet deployed). Each row's `depth` is the deepest 1 m sample along
a road piece, as D-006 in [[decision-log]] records. `floodmap-backend` reads `flood_road_values` for
routing, as before. The road loader and flood-on-roads nodes are marked Built because their code is
in the DAG, but neither task has run on the server yet. The plan is [[raster-first-flood-pipeline]].

TimescaleDB moved from Designed to Built on 2026-10-05 ([[netcdf-values-storage-redesign]],
`US-066`). The DAG's `3b_upload_netcdf_postgres` task (`netcdf_to_pg.py`) runs in parallel with
`3_calculate_depth`, not downstream of it — both depend only on `2_download_results` and
`0b_ensure_schema` finishing, per `dags/flood_mapping_dag.py`'s task graph. It writes the
deduplicated mesh geometry and variable catalog (`mesh_elements`, `netcdf_variable_catalog`) and
the per-timestep values onto a `netcdf_values` hypertable with a 6-hour compression policy and a
48-hour retention policy, replacing a same-named table on `storage-postgres` that had no retention
at all and reached 56 GB during a 48-hour soak test ([[docker-data-vhdx-fills-c-drive-again]]). That
old table is dropped. The dotted `PG -.-> TSDB` edge from the earlier diagram is gone with it: the
DAG writes to TimescaleDB directly, never through `storage-postgres`. `flood_extent_polygon` on
`storage-postgres` also got an automated prune the same week ([[prune-flood-extent-polygon-rows]],
`US-067`), the other table the same incident found growing unbounded.
