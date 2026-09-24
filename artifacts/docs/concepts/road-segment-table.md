---
date: 2026-09-24
type: concept
status: active
tags: [postgis, roads, routing, raster-first, sprint-2]
related: ["[[raster-first-pipeline-stories]]", "[[raster-first-flood-pipeline]]", "[[flood-metric-extractor]]", "[[graphhopper-backend]]", "[[route-forecast-query]]", "[[timescaledb-and-flood-metrics]]"]
last_updated: 2026-09-24
---

# Road segment table

`road_segment` holds the Hanoi road network as short pieces, one row per piece, each with a
`segment_id` that stays the same across loads of the same roads file. It is Story 1 of
[[raster-first-pipeline-stories]]. Flood-on-roads (Story 3), the flood metric extractor, and the
route-forecast query are meant to key their rows by `segment_id` instead of by road name or by a
hash of the geometry.

## Why the table exists

`flood_road_values` stores only `road_name` and geometry for each road piece. Names repeat, and
7,908 of the 12,431 ways in the roads file have no name at all. So each consumer guesses at
identity. `scripts/flood_metrics/extract_run.py`, for example, groups rows by
`md5(ST_AsEWKB(geom_4326))`. The roads file already carries a unique OSM way id in
`properties["@id"]`, for example `way/11835354`, but `scripts/mapping/mapping_geojson.py` drops it.
`road_segment` keeps that id and adds the piece's position on the way.

## Table shape

`scripts/database/create_road_segment_table.py` creates the table. The script is idempotent.

| Column | Type | Meaning |
| --- | --- | --- |
| `segment_id` | `TEXT PRIMARY KEY` | `<way_id>#<piece_index>`, for example `way/11835354#0` |
| `way_id` | `TEXT NOT NULL` | The OSM way id from `@id` |
| `piece_index` | `INTEGER NOT NULL` | Position on the way, counted from 0 at the way's first vertex |
| `road_name` | `TEXT` | `properties.name`, or null for an unnamed way |
| `highway` | `TEXT` | `properties.highway`, the OSM road class |
| `length_m` | `DOUBLE PRECISION NOT NULL` | Piece length in metres, measured in EPSG:3405 |
| `geom` | `geometry(LineString,4326) NOT NULL` | Piece geometry in lon and lat |

The table has a GIST index on `geom` and a unique constraint on `(way_id, piece_index)`, which
also serves lookups by way.

## How the loader cuts a way into pieces

`scripts/roads/load_road_segments.py` exposes `load(conn, roads_path)` and a `main()` for Airflow.
It is not called from `dags/flood_mapping_dag.py` yet. The loader does the following for each way:

1. Transforms the way to EPSG:3405 (VN-2000 / UTM zone 48N), the metric CRS that
   `floodmap/graphhopper-flood-road/backend/flood_areas.py` also uses.
2. Computes the piece count as the length divided by the maximum piece length, rounded up, with a
   minimum of 1.
3. Cuts the way into that many pieces of equal length with `ST_LineSubstring`, so the cut points
   follow distance along the line, not vertex count.
4. Stores each piece's EPSG:3405 length in `length_m` and its geometry, transformed back, in
   `geom`.

Equal pieces avoid the sliver a fixed-length cut leaves at the end of a way. A 120 m way becomes
three 40 m pieces, not two 50 m pieces and a 20 m piece. A way within 1 mm of a whole multiple of
the maximum keeps that many pieces, so float noise from the transform can't add a piece.

The loader runs in one transaction. It stages the file, upserts every piece, skips rows whose
values didn't change, and deletes every row the file no longer produces. A second load of the same
file reports 0 inserted, 0 updated, and 0 deleted. The loader raises before writing anything if a
feature has no `@id`, has a geometry other than `LineString`, or repeats an `@id`. An empty file
also raises, since loading it would delete every row.

## Piece length is 50 m

The default maximum is 50 m, in `DEFAULT_MAX_PIECE_M`. The environment variable
`ROAD_SEGMENT_MAX_PIECE_M` overrides it. The following facts from the real inputs decided the value:

- The depth raster `depth_20260924_170639.tif` has 1 m pixels in EPSG:3405. Even a 10 m piece
  covers several pixels, so raster resolution doesn't limit the choice.
- Way lengths in `toa-do-duong-hanoi.geojson` range from 0.54 m to 6,374 m. The median is 72.5 m,
  the 90th percentile is 253 m, and the total is 1,472.5 km.
- Routing avoids a flooded piece by buffering it by 22 m (`DEFAULT_BUFFER_M` in `flood_areas.py`).
  A piece much longer than the 44 m buffer width makes routing avoid dry road next to a flooded
  spot. A piece much shorter adds rows without changing the avoided area much.

The following table lists the resulting row counts for each candidate maximum:

| Maximum piece | Rows | Ways cut into more than one piece | Longest piece |
| --- | --- | --- | --- |
| 25 m | 65,077 | 10,811 | 25.0 m |
| 50 m | 35,652 | 8,090 | 50.0 m |
| 100 m | 21,415 | 4,523 | 100.0 m |

At 50 m, the mean piece is 41.3 m, close to the 44 m buffer width. So one flooded spot blocks at
most about 50 m of road plus the buffer. At 100 m, a single flooded pixel can close 100 m of a
street that is otherwise dry. At 25 m, the table and every per-timestep table keyed on it grow by
83% over 50 m for a small gain in precision. Story 3 writes one row per piece per timestep, so a
four-timestep run at 50 m is about 143,000 rows.

## Limits of the id

A `segment_id` is stable only while the roads file and the maximum piece length stay the same.
Three changes shift it:

- **An edited way.** If a way's geometry changes, its pieces are cut again. `way/X#1` then covers
  different road, and the loader reports that row as updated.
- **A shorter or longer way.** Pieces are added or dropped at the end of the way. The loader
  deletes the surplus rows.
- **A new maximum piece length.** Almost every id changes meaning. Switching the real file from
  50 m to 100 m updated 17,074 rows and deleted 14,237.

A consumer that stores results across roads loads, such as TimescaleDB history, should do two
things. It should load roads only between runs, never during one. It should also treat a load that
reports any update or delete as a new road version, and keep `length_m` and `geom`, or a hash of
`geom`, next to `segment_id` wherever an old result must still be read against the road it
described.

## Join on `segment_id`

A per-piece result table stores `segment_id` and joins back for the name, class, and geometry:

```sql
SELECT rs.segment_id, rs.road_name, rs.highway, rs.length_m, r.depth, rs.geom
FROM flood_on_road r
JOIN road_segment rs USING (segment_id)
WHERE r.run_ts = %(run_ts)s;
```

`flood_on_road` stands for the Story 3 shadow table, which doesn't exist yet. To find the pieces
near a point, use the GIST index with `ST_DWithin(rs.geom::geography, point::geography, radius_m)`
or a bounding-box filter on `geom`.

## Verification on the real file

The loader was run on 2026-09-24 against a local PostGIS 3.6.4 with the 8.4 MB roads file:

- All 12,431 ways are present, as 35,652 pieces with 35,652 distinct `segment_id` values.
- For every way, the sum of the pieces' `length_m` equals the way's own EPSG:3405 length within
  9.1e-13 m. Measured again from the stored EPSG:4326 geometry, the worst way is off by 6.1e-06 m.
  The story allows 0.5 m.
- The first load took 0.48 s. The second load took 0.29 s and reported 0 changes.
- The table, with indexes, is 11 MB.

To run the tests, point `ROAD_SEGMENT_TEST_DSN` at a PostGIS database and run
`python -m unittest test_load_road_segments` from `scripts/roads/`. The tests skip when the
variable is unset.

## Open items

- Wire the loader into the DAG ([[raster-first-flood-pipeline]], Phase 2 or 3).
- Run `create_road_segment_table.py` and the loader against the server database. The local check
  doesn't show how long the load takes there.
