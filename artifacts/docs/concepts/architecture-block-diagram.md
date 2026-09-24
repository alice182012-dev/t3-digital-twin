---
date: 2026-09-23
type: concept
status: active
tags: [architecture, diagram]
related: ["[[T3-Digital-Twin_Architecture]]", "[[minio-flood-extent-pipeline]]", "[[graphhopper-backend]]", "[[raster-first-flood-pipeline]]"]
last_updated: 2026-09-24
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
    ROUTEEXT["flood-on-roads task<br/>(raster-first Story 3)"]:::designed
    TILEEXT["flood_extent.py + publish.py<br/>(GRASS raster→polygon)"]:::built
  end

  subgraph DATA["Data stores"]
    PG["storage-postgres (PostGIS)<br/>flood_road_values<br/>flood_extent_polygon"]:::built
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
  DEPTH -.-> ROUTEEXT
  DEPTH --> TILEEXT
  ROUTEEXT -.->|flood_road_values| PG
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

The flood-on-roads node is Designed, not built. The GeoJSON chain that used to write
`flood_road_values` (`scripts/mapping/extract_geojson_full.py` through
`scripts/database/geojson_to_pg.py`) left `dags/flood_mapping_dag.py` on 2026-09-24. Until Story 3 of
[[raster-first-pipeline-stories]] lands, no DAG task writes `flood_road_values`, although
`floodmap-backend` still reads it for routing. The plan is [[raster-first-flood-pipeline]].
