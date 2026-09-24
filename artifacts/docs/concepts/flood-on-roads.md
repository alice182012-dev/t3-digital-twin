---
date: 2026-09-24
type: concept
status: active
tags: [postgis, raster, roads, routing, raster-first, sprint-2]
related: ["[[raster-first-pipeline-stories]]", "[[raster-first-flood-pipeline]]", "[[road-segment-table]]", "[[minio-flood-extent-pipeline]]", "[[graphhopper-backend]]", "[[flood-metric-extractor]]"]
last_updated: 2026-09-24
---

# Flood on roads

`scripts/flood_roads/flood_on_roads.py` computes the flood depth on every road piece from one run's
raster tiles and writes it to `flood_road_values`, the table that routing reads through
`floodmap/graphhopper-flood-road/backend/flood_areas.py`. It is Story 3 of
[[raster-first-pipeline-stories]], and it replaces the GeoJSON chain (`scripts/mapping/*` and
`scripts/database/geojson_to_pg.py`). The DAG does not call it yet. Story 4 wires it in.

Inputs are `road_segment` (pieces of at most 50 m, see [[road-segment-table]]) and
`flood_depth_raster_tile` (256 by 256 tiles in EPSG:4326, about 1 m pixels, see
[[minio-flood-extent-pipeline]]).

## Entry points

- `compute(conn, run_ts, target_table="flood_road_values")` replaces the run's rows and returns a
  `ComputeResult` with one `TimestepResult` per timestep: `forecast_time`, `rows`, `wet_pieces`, and
  `sample_seconds`.
- `main(argv)` connects with `db_config.DB_CONFIG` and runs `compute`. From a shell, run
  `python flood_on_roads.py RUN_TS [--target TABLE]`. A target other than `flood_road_values` is
  created first with `create_shadow_table`.
- `create_shadow_table(conn, name)` runs
  `CREATE TABLE IF NOT EXISTS name (LIKE flood_road_values INCLUDING ALL)`. `LIKE` copies columns,
  defaults, and indexes, but not the foreign key to `flood_road_file`.

## Sampling design

Each piece is sampled at the midpoint of every metre along it, with
`ST_LineInterpolatePoint(geom, (i + 0.5) / n)` and `n = ceil(length_m / 1.0)`. `depth` is the mean
of the samples, with dry and nodata samples counted as 0. `depth_max` is the deepest sample. Midpoint
samples each stand for the same length of road, so the mean is a length-weighted mean.

A sample finds its pixel by arithmetic, not by a raster call. The query reads each tile once with
`ST_PixelAsCentroids(rast, 1, true)`, which returns only the wet pixels, and gives each one a global
column and row from its tile's upper-left corner. A sample's global column and row come from its
coordinates, and a join on those two numbers finds its depth. A sample with no wet pixel has depth 0.

Only pieces that touch a tile with at least one wet pixel get sampled. On the real runs 523 of 880
tiles are wet, which leaves 15,285 of 35,652 pieces and 637,277 samples per timestep.

The following timings are for one timestep of run `20260924T164803` on the local PostGIS 3.6.4,
with the same candidate pieces in each row:

| Design | Time | Result |
|---|---|---|
| `ST_Value` per sample, tile found through the hull index | 25.5 s | Reference values |
| `ST_Clip` of each tile to a 0.5 m corridor, then `ST_SummaryStats` | 4.8 s | An area mean. 51 pieces disagree on wet or dry, and the correlation with the line mean is 0.78 |
| Grid join, tile corner read once per wet pixel | 4.1 s to 4.8 s | Identical to `ST_Value` for all 15,285 pieces |
| Grid join, tile corner read once per tile (shipped) | 1.9 s | Identical to `ST_Value` for all 15,285 pieces |

`ST_Value` per sample is slow because each call unpacks the sample's 256 KB tile. The first grid
join still spent 3 s calling `ST_UpperLeftX` once per wet pixel, 1.7 million times, and each call
read the tile again. The shipped query reads the corner once per tile.

A full run of four timesteps took 7.9 s for `20260924T164803` (1.9 s to 2.1 s per timestep) and 7.0 s
for `20260924T170000` (1.7 s per timestep). Sampling takes all but about 0.1 s of each run, so a
production run with more timesteps should grow linearly with their number. The timings come from
`python marie-curie/flood-roads/run_real.py` against the local `flowtest` database. That script is
scratch and is not tracked.

## Which pieces get rows

A piece gets rows when it is wet at any timestep of the run. It then gets one row at every timestep
of the run, with depth 0 at the timesteps where it is dry. A piece that stays dry at every timestep
gets no rows.

Two readers need the zero rows:

- `flood_areas.derive_areas` picks the winner run for a `forecast_time` as the newest `timestamp`
  with rows at that time. If a run wrote nothing at a dry timestep, an older run's flood would win.
- `scripts/flood_metrics/extract_run.py` reads each piece's full series of depths across the run.

The old chain behaved the same way. `merge_geojson.py` filled a cell's dry timesteps with 0, so every
old sliver had a row at every timestep of its run.

On the real runs every timestep has 2,111 rows for `20260924T164803` and 1,716 for
`20260924T170000`. Between 1,486 and 1,970 of them are wet at a given timestep.

## Columns written

`compute` writes the same columns `geojson_to_pg.py` wrote, with the same meanings, plus two new
nullable columns. `scripts/database/create_geojson_tables.py` adds the new columns with
`ADD COLUMN IF NOT EXISTS`, so the old chain keeps working.

| Column | Value | Note |
|---|---|---|
| `file_id` | The `flood_road_file` row with `source_file = 'flood_on_roads_<run_ts>'` | Upserted each run. `feature_count` is the number of pieces with rows, and `geojson_type` is NULL |
| `timestamp` | `run_ts` parsed as naive local time | `20260924T164803` becomes `2026-09-24 16:48:03`, as in `geojson_to_pg.parse_timestamp` |
| `road_name` | `road_segment.road_name`, or `way_id` when the way has no name | The old chain used `@id` as its fallback too |
| `forecast_time` | `valid_time_utc + 7 hours`, naive | Vietnam local time, the time in the `depth_*.tif` file name |
| `depth` | Mean over the samples, in metres | Dry and nodata samples count as 0 |
| `geom`, `geom_4326` | The piece geometry, as GeoJSON and as EPSG:4326 | |
| `depth_max` | Deepest sample, in metres | New. NULL on rows from the old chain |
| `segment_id` | `road_segment.segment_id`, for example `way/11835354#0` | New. NULL on rows from the old chain |

## Retries

`compute` runs in one transaction. It deletes the rows of `(timestamp, forecast_time)` for every
timestep the run has tiles for, then inserts the new rows. A retry therefore converges on the same
rows, and the delete also removes any old-chain rows for the same run and times. Rows of other
runs and other times stay. A transaction-scoped advisory lock on the target table and run keeps two
concurrent writers of one run from both inserting. A run with no tiles raises
`FloodOnRoadsError` and writes nothing.

## Comparison with the old rows

`scripts/flood_roads/compare_with_old.py` compares the new rows of a run with the old chain's rows
of the same run, exported to CSV. It assigns each old sliver to the piece nearest its midpoint. A
piece is impassable under the old rows when any of its slivers reaches the vehicle's limit, which is
how `flood_areas.py` treats them. The limits come from `flood_utils.depth_bands_m` through
`extract_run.impassable_from_m`: motorbike 0.20 m, car 0.30 m, truck 0.35 m, and foot 0.40 m. The
tool also reads the raster along each old sliver, so it can tell a disagreement caused by the old
sampling from one caused by the new rows.

### The old rows sampled a 20 m grid

The old depths come from 20 m cells, not 1 m cells. For all 7,620 old rows of `20260924T164803` and
all 5,764 of `20260924T170000`, the old depth equals the top-left pixel of the 20 m cell that holds
the sliver's midpoint, rounded to 2 decimals. With 1 m cells only 1,835 of 7,620 match. So the
server ran `extract_geojson_full.py` with a `SAMPLE_RATE` of 20, and each old depth is one pixel that
can lie up to 28 m from the road. The check is `marie-curie/flood-roads/old_cell_check.py`.

The consequence is large. Along 3,145 of the 6,234 wet old slivers of `20260924T164803`, and along
2,686 of 4,771 for `20260924T170000`, the raster is dry for the whole sliver. Those slivers were
wet only because their cell's corner pixel was wet. These two counts read the source `.tif` in
EPSG:3405. The comparison tool reads the reprojected tiles and counts 3,147 and 2,676.

### Coverage

The following numbers are summed over the four timesteps of each run.

| Run | Old wet slivers | Raster dry along the sliver | Sliver's piece has a new row | New wet rows | New wet rows with no old sliver |
|---|---|---|---|---|---|
| `20260924T164803` | 6,234 | 3,147 | 3,666 | 7,469 | 4,383 |
| `20260924T170000` | 4,771 | 2,676 | 2,518 | 6,267 | 4,027 |

Every old sliver lies within 1 m of a piece. Of the wet old slivers whose piece has no new row,
2,558 of 2,568 (run 1) and 2,251 of 2,253 (run 2) are dry along the sliver itself. The remaining 12
slivers reach past their piece into a neighbouring piece.

### Depth agreement

The following ranges pair each old wet sliver with its piece and span the four timesteps of a run.
The tool prints the full table per timestep.

| Run | Old depth, average | New mean, average | New max, average | Correlation with mean | Correlation with max |
|---|---|---|---|---|---|
| `20260924T164803` | 0.088 m to 0.111 m | 0.041 m to 0.054 m | 0.123 m to 0.151 m | 0.41 to 0.43 | 0.62 to 0.68 |
| `20260924T170000` | 0.088 m to 0.101 m | 0.040 m to 0.045 m | 0.125 m to 0.138 m | 0.40 to 0.43 | 0.60 to 0.62 |

The old depth sits between the new mean and the new maximum on average, and it correlates only
weakly with either, as expected from a pixel that is often off the road.

### Impassable pieces

The dangerous cell is a piece the old rows closed and the new rows would route through. The
following table sums the pieces over the four timesteps. "Road below the limit" counts the
dangerous pieces where the raster along the old slivers is also under the limit, so the old depth
came from a pixel off the road. The last column is the rest: pieces where the road itself reaches
the limit and the new value does not.

| Run | Vehicle | New value | Old closed, new open | Road below the limit | Road at or over the limit | Old open, new closed |
|---|---|---|---|---|---|---|
| `20260924T164803` | motorbike | mean | 935 | 767 | 168 | 125 |
| `20260924T164803` | motorbike | max | 729 | 729 | 0 | 1,084 |
| `20260924T164803` | car | mean | 593 | 492 | 101 | 52 |
| `20260924T164803` | car | max | 482 | 477 | 5 | 583 |
| `20260924T164803` | truck | mean | 478 | 400 | 78 | 30 |
| `20260924T164803` | truck | max | 385 | 385 | 0 | 439 |
| `20260924T164803` | foot | mean | 381 | 318 | 63 | 16 |
| `20260924T164803` | foot | max | 304 | 304 | 0 | 349 |
| `20260924T170000` | motorbike | mean | 704 | 594 | 110 | 77 |
| `20260924T170000` | motorbike | max | 575 | 571 | 4 | 810 |
| `20260924T170000` | car | mean | 434 | 367 | 67 | 32 |
| `20260924T170000` | car | max | 362 | 362 | 0 | 429 |
| `20260924T170000` | truck | mean | 343 | 283 | 60 | 24 |
| `20260924T170000` | truck | max | 278 | 278 | 0 | 345 |
| `20260924T170000` | foot | mean | 270 | 231 | 39 | 13 |
| `20260924T170000` | foot | max | 225 | 225 | 0 | 282 |

Most of the dangerous cell comes from the old sampling, not from the new rows. With the maximum,
only 9 piece-timesteps remain, and in each of them the adjacent piece of the same way has a maximum
over the limit, because the old sliver crossed into it. With the mean, 39 to 168 piece-timesteps
per vehicle and run are real misses: the road reaches the limit on a short stretch, and the mean
over the piece stays under it. That is the risk the user raised when choosing the mean. The
maximum also closes more pieces the old rows left open (282 to 1,084), because it sees deep pixels
on the road that the 20 m grid skipped.

`flood_areas.py` reads `depth`, so routing uses the mean today. Switching its band filter to
`depth_max` would remove the real misses. That is a routing change and a user decision, not part of
this story.

To rerun the comparison, load the roads and both runs' tiles into a local PostGIS, run
`flood_on_roads.py RUN_TS --target flood_road_values_shadow`, then run
`python scripts/flood_roads/compare_with_old.py RUN_TS OLD_CSV --dsn DSN`. The old CSV files and
depth rasters are in `marie-curie/raster-first/compare/<run>/`, which git ignores.

## Tests

`scripts/flood_roads/test_flood_on_roads.py` runs against a real PostGIS with `postgis_raster` when
`FLOOD_ROADS_TEST_DSN` is set, in its own schema. It builds 10 by 10 tiles of 0.00001 degree pixels
and pieces along pixel rows with known depths. It covers the mean and maximum of a piece with a
wet stretch, dry pieces, a piece across two tiles, a piece wet at one timestep and dry at the next,
the local `timestamp` and `forecast_time`, road name fallback, a rerun beside old-chain rows, the
shadow target, and a run without tiles.

Five deliberate breaks each fail at least one test: averaging only wet samples, dropping the zero
rows at dry timesteps, leaving `forecast_time` in UTC, deleting by run timestamp alone, and sampling
only the first metre of each piece.

## Open items

- `raster_load.load_raster` passes `valid_time_utc` as a timezone-aware value into a `TIMESTAMP`
  column, and PostgreSQL converts it with the session `TimeZone`. On a server whose `TimeZone` is
  not UTC, the stored value is local time, and `forecast_time` here would be 7 hours late. The local
  PostGIS runs with `Asia/Ho_Chi_Minh`, so the comparison loaded tiles with `timezone=UTC`. The
  server's setting is not checked.
- A run that is dry at every timestep writes no rows, as the old chain did. Routing then keeps an
  older run as the winner for those forecast times.
- Routing reads the mean. See the impassable-pieces section for the numbers behind switching to
  `depth_max`.
