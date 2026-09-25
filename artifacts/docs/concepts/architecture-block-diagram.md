---
date: 2026-09-23
type: concept
status: active
tags: [architecture, diagram]
related: ["[[T3-Digital-Twin_Architecture]]", "[[minio-flood-extent-pipeline]]", "[[graphhopper-backend]]", "[[raster-first-flood-pipeline]]", "[[flood-on-roads]]", "[[road-segment-table]]", "[[decision-log]]"]
last_updated: 2026-09-25
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
    DEPTH["calculate_depth.py<br/>depth_*.tif series"]:::built
    RASTERLOAD["raster_load.py<br/>(task 9b_load_depth_raster)"]:::built
    ROADLOAD["load_road_segments.py<br/>(task load_road_segments)"]:::built
    ROUTEEXT["flood_on_roads.py<br/>(task flood_on_roads)"]:::built
    TILEEXT["flood_extent.py + publish.py<br/>(GRASS raster→polygon)"]:::built
  end

  subgraph DATA["Data stores"]
    PG["storage-postgres (PostGIS)<br/>flood_road_values<br/>flood_extent_polygon<br/>flood_depth_raster_tile<br/>road_segment"]:::built
    MINIO["MinIO<br/>flood-extent bucket (.pbf tiles)"]:::built
    TSDB["TimescaleDB"]:::designed
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
  DEPTH --> RASTERLOAD
  RASTERLOAD -->|flood_depth_raster_tile| PG
  ROADLOAD -->|road_segment| PG
  PG -->|tiles, road pieces| ROUTEEXT
  DEPTH --> TILEEXT
  ROUTEEXT -->|flood_road_values| PG
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
  PG -.-> TSDB
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
`flood_depth_raster_tile` and the road pieces from `road_segment`, and runs after
`9b_load_depth_raster` and `load_road_segments`. Each row's `depth` is the deepest 1 m sample along
a road piece, as D-006 in [[decision-log]] records. `floodmap-backend` reads `flood_road_values` for
routing, as before. The road loader and flood-on-roads nodes are marked Built because their code is
in the DAG, but neither task has run on the server yet. The plan is [[raster-first-flood-pipeline]].
