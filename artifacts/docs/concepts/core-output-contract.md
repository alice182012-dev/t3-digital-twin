---
date: 2026-10-07
type: concept
status: active
tags: [contract, core-output, routing, postgis, minio, sprint-11]
related: ["[[EP-10-routing-first-consumer|routing-first-consumer-stories]]", "[[routing-first-consumer-contract]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[edge-depth-table-format]]", "[[graphhopper-backend]]", "[[flood-on-roads]]", "[[US-108-publish-a-run-manifest-for-the-core-outputs|US-108]]"]
last_updated: 2026-10-13
---

# Core output contract

The 3Di pipeline (the Airflow DAGs `flood_mapping_full` and `routing_adapter`) publishes flood results that other applications read.
This page lists what it publishes: nine PostgreSQL tables, the edge depth files, and the vector tiles in MinIO.
Routing is the first consumer.
The story is `US-071` ([[EP-10-routing-first-consumer|routing-first-consumer-stories]] Story C1).

The test `floodmap/graphhopper-flood-road/backend/test_core_contract.py` parses the column tables on this page and compares them with the live database.
It fails when a column name, type, nullability, or position differs, or when a primary key or unique constraint differs.
The `Primary key columns` and `Unique columns` bullets are its input for keys.
The table headings and the `| Column | Type | Nullable |` tables are its input, so change them only together with the schema.
Type is the text of PostgreSQL's `format_type(atttypid, atttypmod)`.

The facts on this page were checked against the code when the page was written.
Each one cites its file.
A fact the code cannot show is marked as unverified.

## Tables

The DDL is in `scripts/database/`.
Task `0b_ensure_schema` of `flood_mapping_full` runs it on every run (`task_ensure_schema`, `dags/flood_mapping_dag.py:168-176`), and every `CREATE` and `ADD COLUMN` in it has `IF NOT EXISTS`.

### demo_pin

One row is the step of the demo flood. The table has at most one row.

| Column | Type | Nullable |
| ------ | ---- | -------- |
| `singleton` | `boolean` | no |
| `run_ts` | `text` | no |
| `valid_time_utc` | `timestamp without time zone` | no |
| `wet_edges` | `integer` | no |
| `chosen_at` | `timestamp without time zone` | no |

- **Key.** The primary key is `singleton`, which a `CHECK` holds at true, so the table cannot hold a second row.
- **Primary key columns.** `singleton`.
- **Meaning.** `run_ts` and `valid_time_utc` name the pinned step, the step with the most wet edges in `edge_depth` when it was chosen.
  `wet_edges` is its count of wet edges.
- **Writer.** `python scripts/database/demo_pin.py` chooses the step and replaces the row.
  `--run` and `--valid-time` take a given step instead.
  Task `0b_ensure_schema` creates the table, and a database without it has no pin.
  On the server (2026-10-13) the row holds run `20261011T001500` at 2026-10-10 19:00 UTC with 2,853 wet edges, and a publish and its prunes left the pinned run in every table and folder.
- **Retention.** The row stays until it is replaced.
  Every prune of a run table keeps the pinned run, and no prune deletes the row:
  `flood_depth_raster_tile`, `flood_extent_step`, `flood_extent_polygon`, `flood_run_output`, `edge_depth` and `edge_depth_run`, the tiles in MinIO, and the edge depth file of the run.
- **Not yet true.** The tile build tiles only the first two steps of a run, so the pinned step has tiles only when it is one of them ([[US-126-rebuild-the-raster-tiles-and-road-values-from-the-netcdf|US-126]] rebuilds the others).

### edge_depth

One row is the depth of one wet edge at one forecast time, from one run.

| Column | Type | Nullable |
| ------ | ---- | -------- |
| `run_ts` | `text` | no |
| `valid_time_utc` | `timestamp without time zone` | no |
| `edge_key` | `text` | no |
| `depth_cm` | `integer` | no |

- **Key.** The primary key is (`run_ts`, `valid_time_utc`, `edge_key`).
  `run_ts` references `edge_depth_run.run_ts` with `ON DELETE CASCADE`.
- **Primary key columns.** `run_ts`, `valid_time_utc`, `edge_key`.
- **Time.** `run_ts` and `valid_time_utc` follow the Time convention section.
- **Units.** `depth_cm` is the deepest sample along the edge, in whole centimetres, and a check keeps it above 0.
- **Which rows exist.** An edge that is dry at a time has no row for that time.
  A run with no wet edge has no rows here.
- **Join.** `edge_key` is `graph_edge.edge_key`, which survives a re-import of the same OSM file.
  The routing backend joins on it to draw the geometry (`floodmap/graphhopper-flood-road/backend/flood_areas.py`).
- **Writer.** Task `9c_build_edge_depth_table`, in one transaction before it writes the file and publishes (`scripts/edge_depth/edge_depth_rows.py`).
  A rebuild of one run replaces its rows.
- **Retention.** The 24 hours before the newest run, set by `EDGE_DEPTH_KEEP_HOURS` (`edge_depth_rows.py`).

### edge_depth_run

One row is one run whose edge depth `9c` has written, wet or dry.

| Column | Type | Nullable |
| ------ | ---- | -------- |
| `run_ts` | `text` | no |
| `graph_hash` | `text` | no |
| `valid_times` | `timestamp without time zone[]` | no |
| `built_at` | `timestamp without time zone` | no |

- **Key.** The primary key is `run_ts`.
- **Primary key columns.** `run_ts`.
- **Time.** `valid_times` holds the forecast times the run covers, in UTC without an offset, like `valid_time_utc`.
  `built_at` is `NOW()` cast to `timestamp without time zone`.
- **Why it exists.** A run with no wet edge writes no rows to `edge_depth`, so this row is the only record that the run covers a time.
  The newest run whose `valid_times` contains a time wins that time (`_LATEST_WINNER` in `flood_areas.py`).
  A winner with no rows in `edge_depth` means no edge is wet at that time.
- **Writer.** Task `9c_build_edge_depth_table`, in the same transaction as the rows in `edge_depth`.
- **Retention.** The same prune as `edge_depth`, which deletes the registry row and, by cascade, its rows.

### flood_depth_raster_tile

One row is one 256 by 256 pixel tile of the flood depth raster at one forecast step of one run.

| Column | Type | Nullable |
| ------ | ---- | -------- |
| `run_ts` | `text` | no |
| `valid_time_utc` | `timestamp without time zone` | no |
| `tile_x` | `integer` | no |
| `tile_y` | `integer` | no |
| `rast` | `raster` | no |
| `created_at` | `timestamp without time zone` | yes |

- **Key.** The primary key is (`run_ts`, `valid_time_utc`, `tile_y`, `tile_x`).
  `tile_x` and `tile_y` count tiles from the raster's upper-left corner.
- **Primary key columns.** `run_ts`, `valid_time_utc`, `tile_y`, `tile_x`.
- **Units.** Band 1 of `rast` is the water depth in metres.
  Inside the raster, a dry cell and a cell outside the model both read 0, and 0 is the band's NoData value (`floodmap/graphhopper-flood-road/backend/flood_points.py:111-113`).
- **CRS.** EPSG:4326.
  Task `9b_load_depth_raster` reprojects each depth file from the model's EPSG:3405 with nearest-neighbour sampling before it loads it (`scripts/flood_extent/raster_load.py:55-59`).
- **Writer.** `9b_load_depth_raster` calls `raster_load.load_run`.
  It loads every forecast step of the run, and it replaces all tiles of one step in one transaction (`raster_load.py:62-80`).
- **Retention.** The newest 8 runs by `run_ts`.
  `FLOOD_RASTER_KEEP_RUNS` changes the number, and the run being loaded is never pruned (`raster_load.py:34`, `raster_load.py:83-103`).

### flood_extent_polygon

One row is the dissolved polygon of one depth band at one forecast step of one run.

| Column | Type | Nullable |
| ------ | ---- | -------- |
| `id` | `bigint` | no |
| `run_ts` | `text` | no |
| `valid_time_utc` | `timestamp without time zone` | no |
| `dn_code` | `integer` | no |
| `area_m2` | `double precision` | no |
| `geom` | `geometry(Geometry,4326)` | no |
| `created_at` | `timestamp without time zone` | yes |

- **Key.** The primary key is `id`.
  (`run_ts`, `valid_time_utc`, `dn_code`) is unique, and the writer upserts on it.
- **Primary key columns.** `id`.
- **Unique columns.** `run_ts`, `valid_time_utc`, `dn_code`.
- **Units.** `dn_code` names the band by its upper limit in centimetres.
  10 is a depth over 0.05 m up to 0.1 m, and so on to 60, which ends at 0.6 m.
  600 is any depth over 0.6 m.
  A depth of 0.05 m or less is dry and has no row (`BAND_TABLE` and `TOP_CODE` in `scripts/flood_extent/flood_extent.py:41-44`).
  `area_m2` is in square metres, measured in the model's projected CRS before the polygon is reprojected (`flood_extent.py:199-207`).
- **CRS.** EPSG:4326.
- **Writer.** Task `9_build_flood_tiles` of the DAG `flood_tiles` calls `publish.publish_run` (`scripts/flood_extent/publish.py:49-76`).
  It writes only the first `FLOOD_EXTENT_TILE_STEPS` steps of a run, 2 by default (`dags/flood_tiles_dag.py`).
  A dry step has no rows.
- **Retention.** The newest 8 runs by `run_ts` (`prune_polygon_rows`, `publish.py:135-169`).
  `FLOOD_EXTENT_KEEP_RUNS` changes the number.

### flood_extent_step

One row says that one forecast step of one run is fully published: its tiles are in MinIO and its polygon rows are committed.

| Column | Type | Nullable |
| ------ | ---- | -------- |
| `run_ts` | `text` | no |
| `valid_time_utc` | `timestamp without time zone` | no |
| `is_empty` | `boolean` | no |
| `published_at` | `timestamp without time zone` | yes |

- **Key.** The primary key is (`run_ts`, `valid_time_utc`).
- **Primary key columns.** `run_ts`, `valid_time_utc`.
- **Meaning of `is_empty`.** `true` means the step is dry.
  A dry step has a row here and no rows in `flood_extent_polygon`.
- **Writer.** `9_build_flood_tiles`.
  The writer inserts the step row in the same transaction as the step's polygon rows, after the step's tiles are uploaded (`publish.py:49-76`, `publish.py:222-227`).
  A rewrite sets `published_at` to `NOW()` again.
- **Retention.** The newest 8 runs by `run_ts` (`prune_step_rows`, `publish.py:113-132`).

### flood_run_output

One row says that one output of one run is published.

| Column | Type | Nullable |
| ------ | ---- | -------- |
| `run_ts` | `text` | no |
| `output` | `text` | no |
| `published_at` | `timestamp without time zone` | no |

- **Key.** The primary key is (`run_ts`, `output`).
- **Primary key columns.** `run_ts`, `output`.
- **Outputs.** The `output` column holds one of three values.
  Each value names the task that writes its row.
  - `depth_raster`: task `9b_load_depth_raster` of `flood_mapping_full`, in the same transaction as the tiles in `flood_depth_raster_tile`.
  - `extent`: task `9_build_flood_tiles`, after the last tile step.
  - `edge_depth`: task `9c_build_edge_depth_table`, after the file rename, when `latest` names that file.
- **Writer.** Each task writes its row only after its output is published.
  A failed task writes no row for that run.
  A rewrite sets `published_at` to `NOW()` again.
- **Retention.** The newest 8 runs by `run_ts`.
  `FLOOD_EXTENT_KEEP_RUNS` changes the number.
  The prune runs when task `9_build_flood_tiles` publishes, and it keeps the run being published.

### forecast_mode

One row is one rain gate decision of one run of `flood_mapping_full`.

| Column | Type | Nullable |
| ------ | ---- | -------- |
| `slot` | `timestamp without time zone` | no |
| `decided_at` | `timestamp without time zone` | no |
| `rain_peak_mm_hr` | `double precision` | no |
| `gate_mm_hr` | `double precision` | no |
| `standing_flood` | `boolean` | yes |
| `mode` | `text` | no |

- **Key.** The primary key is `slot`.
- **Primary key columns.** `slot`.
- **Time.** `slot` is the 15-minute slot of the DAG run, in UTC without an offset.
  `decided_at` is `NOW()` cast to `timestamp without time zone`.
- **Mode.** `mode` is `LIVE`, `PENDING`, or `DEMO` (a `CHECK` allows only these).
  - `LIVE`: the gate is open, and a `depth_raster` row of `flood_run_output` is younger than 45 minutes.
  - `PENDING`: the gate is open, and no such row exists. The simulation is still running.
  - `DEMO`: the gate is closed, so no rain above `gate_mm_hr` is forecast and no flood stands.
- **Fields.** `rain_peak_mm_hr` is the forecast peak and `gate_mm_hr` is the threshold (`FLOOD_RAIN_THRESHOLD_MM_HR`).
  `standing_flood` is NULL when the forecast rain alone opened the gate, because the task does not read the flood then.
- **Reading.** The newest row by `slot` is the current mode.
  The role `routing_reader` can `SELECT` the table and cannot `INSERT` into it (checked on the server on 2026-10-13).
- **Writer.** Task `0_check_forecast_rain` writes the row on every decision, and it creates the table, because a dry state ends the run before `0b_ensure_schema` (`scripts/forecast_mode.py`).
  Task `9b_load_depth_raster` moves the row of its slot from `PENDING` to `LIVE` after the depth rasters are published.
  A failed write is printed and does not stop the gate or `9b`.
- **Retention.** The last 7 days, deleted at each write.

### graph_edge

One row is one edge of the GraphHopper graph.

| Column | Type | Nullable |
| ------ | ---- | -------- |
| `edge_id` | `integer` | no |
| `length_m` | `double precision` | no |
| `geom` | `geometry(LineString,4326)` | no |
| `edge_key` | `text` | yes |

- **Key.** The primary key is `edge_id`, GraphHopper's own edge id.
  It changes when the graph is imported again (`scripts/database/create_graph_edge_table.py:8-20`).
- **Stable key.** `edge_key` is `<osm_way_id>:<position along the way>`, with a unique index.
  It is the same when the same OSM file is imported again.
  It is NULL for every row until the export is in format 3, which needs `osm_way_id` in `graph.encoded_values` ([[US-117-export-a-stable-key-with-each-graph-edge|US-117]]).
- **Primary key columns.** `edge_id`.
- **Units.** `length_m` is the geodesic length in metres, `ST_Length(geom::geography)` (`scripts/edge_depth/graph_edges.py:129`).
- **CRS.** EPSG:4326.
- **Writer.** Task `9c_build_edge_depth_table` loads the graph export when its hash differs from the hash in `graph_edge_export`.
  It replaces the whole table in one transaction (`graph_edges.py:144-164`).
- **Retention.** One graph at a time.
  The routing backend reads its geometry to draw the wet edges of `edge_depth` (`US-119`).
  Task 9c reads it to build the edge depth files.

## Edge depth files

Task `9c_build_edge_depth_table` writes one file per run, `<run_ts>.bin`, into the Docker volume `edge-depth-tables`.
A text file named `latest` holds the name of the current file.
The newest 8 files stay (`EDGE_TABLE_KEEP_RUNS`, default 8 in `dags/routing_adapter_dag.py` and in `compose.yml`, [[decision-log|D-033]]).
Depths are in centimetres, and the step times are seconds since 1970-01-01T00:00:00Z.
The byte layout, the `latest` pointer, and the graph hash check are in [[edge-depth-table-format]].

## Tiles in MinIO

Task `9_build_flood_tiles` uploads Mapbox Vector Tiles of the flood extent polygons.

- **Bucket.** `flood-extent`, set by `FLOOD_EXTENT_BUCKET` (`dags/flood_mapping_dag.py:58`).
  `minio-init` gives the bucket an anonymous download policy (`compose.yml:129-133`).
- **Object name.** `runs/<run_ts>/<timestep_key>/<z>/<x>/<y>.pbf`.
  `timestep_key` is the time in the step's depth file name, in the form `YYYYMMDDTHHMMSS` (`publish.py:79-91`, `stamp_key` in `flood_extent.py:326-331`).
  The content type is `application/x-protobuf`.
- **Content.** One layer named `flood_extent`, zoom levels 10 to 16.
  Each feature has the band code in the field `DN`, with the same values as `flood_extent_polygon.dn_code` (`flood_extent.py:186-192`, defaults in `flood_extent.py:315-316`).
  The code does not set a tiling scheme, so the tiles use GDAL's default MVT grid.
  This page does not verify which grid that is.
- **Which steps.** Only the first `FLOOD_EXTENT_TILE_STEPS` steps of a run, and only wet ones.
  A dry step has no objects.
- **Retention.** The newest 8 runs by `run_ts` prefix (`prune_bucket_runs`, `publish.py:94-110`).

## Time convention

The database stores forecast step times in UTC, and file and object names carry Vietnam local time (+07).
Two exceptions apply.

- **`valid_time_utc`.** UTC without an offset, in `flood_depth_raster_tile`, `flood_extent_polygon`, and `flood_extent_step`.
  `publish.valid_time_utc` converts the +07 time in the depth file name to UTC (`publish.py:30-39`).
- **`run_ts`.** Text, not a time.
  It is the +07 time of the run's earliest depth file, in the form `YYYYMMDDTHHMMSS` (`run_ts_for_depth_dir` in `flood_extent.py:334-342`).
  It is fixed width, so its text order is its time order.
- **Names.** The depth file names, the tile object names, and the `.bin` file names use the same +07 form.
- **`created_at` and `published_at`.** `NOW()` cast to `timestamp without time zone`, so they use the database session's time zone.
  The repository does not set that time zone, so this page does not verify that it is UTC.

## Readiness

A row in `flood_extent_step` is the signal that a step is published.
Its `published_at` is when the writer committed it.
A consumer that sees the row can read the step's tiles and polygon rows.

The row covers only the outputs of task `9_build_flood_tiles`.
Task `9b_load_depth_raster` writes `flood_depth_raster_tile` in parallel and can finish before or after it.
When 9b succeeds, it emits the Airflow asset `flood_depth_raster_tile` with `{"run_ts": "<run_ts>"}` in the event's `extra` (`dags/core_assets.py`, `US-073`).
The event says that every timestep of that run is in `flood_depth_raster_tile`.
The DAG `routing_adapter` runs on it, and its task `9c_build_edge_depth_table` writes the `edge_depth` output for that run.
Then `9c` emits the Airflow asset `edge_depth` (`EDGE_DEPTH_ROWS` in `dags/core_assets.py`) with `{"run_ts": "<run_ts>"}`, after the rows of `edge_depth` and `edge_depth_run` are committed, and the DAG `flood_history` runs on that event.
A consumer outside Airflow reads `flood_run_output` instead of polling three places: the rows of `flood_depth_raster_tile`, the rows of `flood_extent_polygon`, and the file that `latest` names.
`artifacts/TODOS.md` records `routing_adapter` as running on the server from 2026-10-07 16:00 +07.
The timing of the asset trigger on the server is still being read (`US-073`).

## Retention

| Output | Kept | Set by |
| ------ | ---- | ------ |
| `flood_depth_raster_tile` | Newest 8 runs | `FLOOD_RASTER_KEEP_RUNS`, `raster_load.py` |
| `flood_extent_polygon` | Newest 8 runs | `FLOOD_EXTENT_KEEP_RUNS`, `publish.py` |
| `flood_extent_step` | Newest 8 runs | `FLOOD_EXTENT_KEEP_RUNS`, `publish.py` |
| Tiles in `flood-extent` | Newest 8 runs | `FLOOD_EXTENT_KEEP_RUNS`, `publish.py` |
| `flood_run_output` (US-108) | Newest 8 runs | `FLOOD_EXTENT_KEEP_RUNS`, task `9_build_flood_tiles` |
| `edge_depth`, `edge_depth_run` | The 24 hours before the newest run | `EDGE_DEPTH_KEEP_HOURS`, `edge_depth_rows.py` |
| `graph_edge` | The loaded graph | `graph_edges.py` |
| Edge depth files | Newest 8 runs | `EDGE_TABLE_KEEP_RUNS`, `publish_edge_depth.py` |

The prunes of the four run tables and the bucket keep the run being published, even when it is older than the newest 8.
The prune of the edge depth files keeps the file that `latest` names (`_retain` in `scripts/edge_depth/publish_edge_depth.py`).
`netcdf_values` is not a contract table.
It holds the raw 3Di results, and no code outside `scripts/database/` reads it.

## Reader roles

Each consumer application connects as its own role, and the role can read only the tables listed for it in the following subsections (`US-072`, `US-107`).
The script `scripts/database/create_routing_reader_role.py` takes a role name as its argument and reads that role's table list from this page with `core_contract.parse_reader_roles`.
It revokes the role's other table rights and its `CREATE` right on schema `public`, then grants `SELECT` on each listed table.
Rerun it for a role after its list changes.
The script runs in the Airflow worker, which mounts `core_contract.py` and this page read-only ([[US-132-let-the-worker-run-the-reader-role-script|US-132]]).
The parser fails when a role lists no table, lists a table this page does not describe, or appears twice.

- **Name.** The variable `<ROLE>_USER`, where `<ROLE>` is the role name in uppercase, sets the PostgreSQL role name.
  The default is the role name itself.
- **Password.** The variable `<ROLE>_PASSWORD` in `.env` holds the password.
  The script refuses to run without it.
- **PostGIS.** A role needs no extra grant.
  PostGIS functions are executable by `PUBLIC`, and `spatial_ref_sys`, `geometry_columns`, and `raster_columns` are readable by `PUBLIC`.
  This was read from the server catalog on 2026-10-07.
- **New tables.** A table the writer creates later is not readable by any role, because the database has no default privileges.
  `TRUNCATE` keeps the grant.
- **Test.** `floodmap/graphhopper-flood-road/backend/test_reader_role.py` connects with the backend's settings, `POSTGRES_USER` and `POSTGRES_PASSWORD`.
  It checks that `SELECT` works on each table of the role, and that writes, a read of `flood_segment_metrics` (a table outside every contract list), and a read of a contract table outside the role's list fail with a permission error.

### routing_reader

The routing backend `floodmap-backend` connects as this role.
Its variables are `ROUTING_READER_USER` and `ROUTING_READER_PASSWORD`, and the service in `compose.yml` has no fallback to the writer role.

- `demo_pin`
- `edge_depth`
- `edge_depth_run`
- `flood_depth_raster_tile`
- `flood_extent_polygon`
- `flood_extent_step`
- `flood_run_output`
- `forecast_mode`
- `graph_edge`

### analysis_reader

An analysis application connects as this role. The service that runs it is described in [[analysis-service]].
Its variables are `ANALYSIS_READER_USER` and `ANALYSIS_READER_PASSWORD`.
It reads the flood results and not the road graph, so `graph_edge` is not on its list.

- `flood_extent_step`
- `flood_extent_polygon`
- `flood_depth_raster_tile`
- `flood_run_output`
