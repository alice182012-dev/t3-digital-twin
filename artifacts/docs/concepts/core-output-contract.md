---
date: 2026-10-07
type: concept
status: active
tags: [contract, core-output, routing, postgis, minio, sprint-11]
related: ["[[EP-10-routing-first-consumer|routing-first-consumer-stories]]", "[[routing-first-consumer-contract]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[edge-depth-table-format]]", "[[graphhopper-backend]]", "[[flood-on-roads]]", "[[US-108-publish-a-run-manifest-for-the-core-outputs|US-108]]"]
last_updated: 2026-10-12
---

# Core output contract

The 3Di pipeline (the Airflow DAGs `flood_mapping_full` and `routing_adapter`) publishes flood results that other applications read.
This page lists what it publishes: seven PostgreSQL tables, the edge depth files, and the vector tiles in MinIO.
Routing is the first consumer.
The story is `US-071` ([[EP-10-routing-first-consumer|routing-first-consumer-stories]] Story C1).

The test `floodmap/graphhopper-flood-road/backend/test_core_contract.py` parses the seven column tables on this page and compares them with the live database.
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

### flood_road_file

One row registers one run of `flood_on_roads`, whether or not the run has any wet road piece.

| Column | Type | Nullable |
| ------ | ---- | -------- |
| `id` | `bigint` | no |
| `timestamp` | `timestamp without time zone` | no |
| `source_file` | `text` | no |
| `geojson_type` | `text` | yes |
| `feature_count` | `integer` | yes |
| `created_at` | `timestamp without time zone` | yes |
| `forecast_times` | `timestamp without time zone[]` | yes |

- **Key.** The primary key is `id`.
  `source_file` is unique, and it is `flood_on_roads_<run_ts>`.
- **Primary key columns.** `id`.
- **Unique columns.** `source_file`.
- **Time.** `timestamp` is the run, in Vietnam local time (+07) without an offset, the same value as `flood_road_values.timestamp`.
  `forecast_times` holds the forecast times the run covers, in the same local time as `flood_road_values.forecast_time`.
- **Why it exists.** A run in which no road piece is wet writes no rows to `flood_road_values`, so the registry is the only record that the run covers a time.
  The newest run whose `forecast_times` contains a time wins that time (`_WINNER_SEG_SQL` in `flood_areas.py`).
  A winner with no rows in `flood_road_values` means no road piece is wet at that time.
- **Which rows exist.** The writer registers every run, including a run with `feature_count` 0.
  A run from the older GeoJSON chain, `scripts/database/geojson_to_pg.py`, has `forecast_times` NULL until `create_flood_road_tables.py` backfills it from its rows.
  A shadow run (`flood_on_roads.py --target`) registers no times.
- **Writer.** Task `flood_on_roads` of the DAG `routing_adapter`, in the same transaction as its rows in `flood_road_values`.
- **Retention.** The prune of `flood_road_values` deletes the registry rows of the runs it deletes.
  A run with no rows in `flood_road_values` is not found by that prune, so its registry row stays.
  The rows are small, and an old row covers only past times.

### flood_road_values

One row is the flood depth of one road piece at one forecast time, from one run.

| Column | Type | Nullable |
| ------ | ---- | -------- |
| `id` | `bigint` | no |
| `file_id` | `bigint` | no |
| `timestamp` | `timestamp without time zone` | no |
| `road_name` | `text` | yes |
| `forecast_time` | `timestamp without time zone` | no |
| `depth` | `double precision` | yes |
| `geom` | `jsonb` | yes |
| `created_at` | `timestamp without time zone` | yes |
| `geom_4326` | `geometry(Geometry,4326)` | yes |
| `segment_id` | `text` | yes |

- **Key.** The primary key is `id`.
  `file_id` references `flood_road_file.id` with `ON DELETE CASCADE`.
  No constraint makes (`timestamp`, `forecast_time`, `segment_id`) unique.
  The writer keeps it unique: it deletes the run's rows for those forecast times and inserts new ones in one transaction, under an advisory lock (`scripts/flood_roads/flood_on_roads.py:176-224`).
- **Primary key columns.** `id`.
- **Time.** `timestamp` is the run, and `forecast_time` is the forecast step.
  Both are Vietnam local time (+07) without an offset, not UTC.
  `timestamp` is `run_ts` read as a time, and `forecast_time` is `valid_time_utc` plus 7 hours (`flood_on_roads.py:30-32`, `flood_on_roads.py:59-61`, `flood_on_roads.py:211`).
- **Units.** `depth` is in metres.
  It is the deepest of the samples taken every 1 m along the piece (decision D-006, `flood_on_roads.py:1-11`).
- **CRS.** `geom_4326` is EPSG:4326.
  `geom` is the same line as GeoJSON text.
- **Which rows exist.** A piece that is wet at any step of a run gets a row at every step of that run, with 0 where it is dry.
  A piece that is dry at every step has no row (`flood_on_roads.py:148-167`).
  `segment_id` is the id of the piece in `road_segment`.
  It is NULL on rows from the older GeoJSON chain, `scripts/database/geojson_to_pg.py`, which `flood_mapping_full` does not call.
- **Writer.** Task `flood_on_roads` of the DAG `routing_adapter` calls `flood_on_roads.compute`.
  It runs on the `FLOOD_DEPTH_RASTER` event of `9b_load_depth_raster` and after `load_road_segments` (`dags/routing_adapter_dag.py:145-159`, `dags/routing_adapter_dag.py:198`).
- **Retention.** None found.
  No code in `dags/` or `scripts/` deletes old runs from this table, so it keeps every run.
  This is unverified on the live server.
  `US-086` (Sprint 12, not started) adds a prune.

### flood_run_output

One row says that one output of one run is published.

| Column | Type | Nullable |
| ------ | ---- | -------- |
| `run_ts` | `text` | no |
| `output` | `text` | no |
| `published_at` | `timestamp without time zone` | no |

- **Key.** The primary key is (`run_ts`, `output`).
- **Primary key columns.** `run_ts`, `output`.
- **Outputs.** The `output` column holds one of four values.
  Each value names the task that writes its row.
  - `depth_raster`: task `9b_load_depth_raster` of `flood_mapping_full`, in the same transaction as the tiles in `flood_depth_raster_tile`.
  - `extent`: task `9_build_flood_tiles`, after the last tile step.
  - `road_values`: task `flood_on_roads` of `routing_adapter`, in the same transaction as its rows in `flood_road_values`.
  - `edge_depth`: task `9c_build_edge_depth_table`, after the file rename, when `latest` names that file.
- **Writer.** Each task writes its row only after its output is published.
  A failed task writes no row for that run.
  A rewrite sets `published_at` to `NOW()` again.
- **Retention.** The newest 8 runs by `run_ts`.
  `FLOOD_EXTENT_KEEP_RUNS` changes the number.
  The prune runs when task `9_build_flood_tiles` publishes, and it keeps the run being published.

### graph_edge

One row is one edge of the GraphHopper graph.

| Column | Type | Nullable |
| ------ | ---- | -------- |
| `edge_id` | `integer` | no |
| `length_m` | `double precision` | no |
| `geom` | `geometry(LineString,4326)` | no |

- **Key.** The primary key is `edge_id`, GraphHopper's own edge id.
  It changes when the graph is imported again (`scripts/database/create_graph_edge_table.py:8-14`).
- **Primary key columns.** `edge_id`.
- **Units.** `length_m` is the geodesic length in metres, `ST_Length(geom::geography)` (`scripts/edge_depth/graph_edges.py:101-106`).
- **CRS.** EPSG:4326.
- **Writer.** Task `9c_build_edge_depth_table` loads the graph export when its hash differs from the hash in `graph_edge_export`.
  It replaces the whole table in one transaction (`graph_edges.py:118-138`).
- **Retention.** One graph at a time.
  The routing backend does not read this table.
  Task 9c reads it to build the edge depth files.

## Edge depth files

Task `9c_build_edge_depth_table` writes one file per run, `<run_ts>.bin`, into the Docker volume `edge-depth-tables`.
A text file named `latest` holds the name of the current file.
The newest 3 files stay (`EDGE_TABLE_KEEP_RUNS`, `dags/routing_adapter_dag.py:42`).
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
- **Exception: `flood_road_values`.** `timestamp` and `forecast_time` are +07 without an offset (see the table section earlier on this page).
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
The DAG `routing_adapter` runs on it, and its tasks `flood_on_roads` and `9c_build_edge_depth_table` write the other two outputs for that run.
A consumer outside Airflow reads `flood_run_output` instead of polling three places: the rows of `flood_depth_raster_tile`, the rows of `flood_road_values`, and the file that `latest` names.
`artifacts/TODOS.md` records `routing_adapter` as running on the server from 2026-10-07 16:00 +07.
The timing of the asset trigger on the server is still being read (`US-073`).

## Retention

| Output | Kept | Set by |
| ------ | ---- | ------ |
| `flood_depth_raster_tile` | Newest 8 runs | `FLOOD_RASTER_KEEP_RUNS`, `raster_load.py` |
| `flood_extent_polygon` | Newest 8 runs | `FLOOD_EXTENT_KEEP_RUNS`, `publish.py` |
| `flood_extent_step` | Newest 8 runs | `FLOOD_EXTENT_KEEP_RUNS`, `publish.py` |
| Tiles in `flood-extent` | Newest 8 runs | `FLOOD_EXTENT_KEEP_RUNS`, `publish.py` |
| `flood_road_values` | Rows older than `FLOOD_ROAD_VALUES_KEEP_HOURS` (default 24) before the newest run, pruned by the task `prune_flood_road_values` (US-086, D-017) | 45 runs and 1,087,512 rows after the first prune on 2026-10-09, from 413 runs and 14,836,828 rows (7,398 MB). After `VACUUM FULL` the table with its indexes is 537 MB |
| `flood_run_output` (US-108) | Newest 8 runs | `FLOOD_EXTENT_KEEP_RUNS`, task `9_build_flood_tiles` |
| `graph_edge` | The loaded graph | `graph_edges.py` |
| Edge depth files | Newest 3 runs | `EDGE_TABLE_KEEP_RUNS`, `publish_edge_depth.py` |

The prunes of the four run tables and the bucket keep the run being published, even when it is older than the newest 8.
The prune of the edge depth files keeps the file that `latest` names (`_retain` in `scripts/edge_depth/publish_edge_depth.py`).
`netcdf_values` is not a contract table.
It holds the raw 3Di results, and no code outside `scripts/database/` reads it.

## Reader roles

Each consumer application connects as its own role, and the role can read only the tables listed for it in the following subsections (`US-072`, `US-107`).
The script `scripts/database/create_routing_reader_role.py` takes a role name as its argument and reads that role's table list from this page with `core_contract.parse_reader_roles`.
It revokes the role's other table rights and its `CREATE` right on schema `public`, then grants `SELECT` on each listed table.
Rerun it for a role after its list changes.
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
  It checks that `SELECT` works on each table of the role, and that writes, a read of `road_segment`, and a read of a contract table outside the role's list fail with a permission error.

### routing_reader

The routing backend `floodmap-backend` connects as this role.
Its variables are `ROUTING_READER_USER` and `ROUTING_READER_PASSWORD`, and the service in `compose.yml` has no fallback to the writer role.

- `flood_depth_raster_tile`
- `flood_extent_polygon`
- `flood_extent_step`
- `flood_road_file`
- `flood_road_values`
- `flood_run_output`
- `graph_edge`

### analysis_reader

An analysis application connects as this role.
Its variables are `ANALYSIS_READER_USER` and `ANALYSIS_READER_PASSWORD`.
It reads the flood results and not the road graph, so `graph_edge` and `road_segment` are not on its list.

- `flood_road_values`
- `flood_extent_step`
- `flood_extent_polygon`
- `flood_depth_raster_tile`
- `flood_run_output`
