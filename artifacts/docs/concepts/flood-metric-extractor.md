---
date: 2026-09-23
type: concept
status: active
tags: [flood-metrics, postgis, sprint-2]
related: ["[[EP-04-timescaledb-and-flood-metrics|timescaledb-and-flood-metrics]]", "[[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]]", "[[T3-Digital-Twin_Architecture]]", "[[routing-depth-threshold-model]]", "[[timescaledb-schema]]", "[[decision-log]]"]
last_updated: 2026-10-13
---

# Flood metric extractor

The flood metric extractor turns one run's per-segment depth series into flood-impact metrics for
each graph edge and vehicle type. It is Story 3 of [[EP-04-timescaledb-and-flood-metrics|timescaledb-and-flood-metrics]], and it
implements the metrics that section 4.4 of [[T3-Digital-Twin_Architecture]] lists. No DAG task
runs it yet.

## Code and data flow

- `scripts/flood_metrics/metrics.py` holds the computation. `extract(series, impassable_from_m)`
  is a pure function. It takes a `DepthSeries` (timestamps and depths in metres) and a map from
  vehicle type to hard-block depth, and it returns a `SegmentMetrics`.
- `scripts/flood_metrics/extract_run.py` is the shell around `extract`. It reads one run from
  `edge_depth` and `edge_depth_run`, groups the rows into one series per edge, and writes the results.
  `edge_depth` holds the wet edges only, so the script fills each dry step of a wet edge with 0 from
  `edge_depth_run.valid_times`. The depth is the deepest sample along the edge, in whole centimetres,
  which is the value the routing engine reads ([[decision-log|D-038]]). The geometry comes from `graph_edge`.
  A run that has no wet edge writes no rows. A run that `edge_depth_run` does not list is an error.
- `scripts/database/create_flood_metrics_tables.py` creates the output table,
  `flood_segment_metrics`, in `storage-postgres`. The script is idempotent.

To extract one run, run the table script once, then run `python
scripts/flood_metrics/extract_run.py RUN_TS`, where `RUN_TS` is the run folder name, such as
`20260923T100000`. The loader selects the `edge_depth` rows of that run. The writer deletes the run's
earlier edge-keyed rows and inserts the new rows in one transaction, so a rerun replaces the earlier
result. Rows of the piece-based extraction stay.

The output table lives in `storage-postgres` instead of TimescaleDB, so the extractor works
without the TimescaleDB service. Nothing copies `flood_segment_metrics` into TimescaleDB. The story that
would have (`US-021`) was dropped on 2026-10-01 (D-009 in [[decision-log]]).

## Edge key

A row has `edge_key`, which is `graph_edge.edge_key` (`<osm_way_id>:<position along the way>`).
The table is unique on `(run_ts, edge_key, vehicle_type)` for these rows.
A row has no `road_name`, because `graph_edge` has no name. To report a road, group the rows by the
way id in the key.
The metric times are local time (UTC+7), as in the rows written before, while the edge depth tables hold UTC.

Rows from before US-121 have `segment_key`, which is `md5(ST_AsEWKB(geom_4326))` of the piece, and no
`edge_key`. They are kept, and a check allows exactly one of the two keys per row.
After a graph re-import, a row keeps its key. Read a key by the rule in [[graph-reimport-procedure]].

On the server (2026-10-13), `extract_run.py 20261010T223000` wrote 11,496 rows, which is 2,874 edges times 4 vehicle types.
The share of wet edges that each vehicle cannot pass is within 2 points of the share of wet pieces from the deleted table `flood_road_values` (car 16.7% and 15.1%, motorbike 27.3% and 25.3%).
The edge count is higher because the graph has more edges than the run has pieces.

## Metric definitions

"T" is the first timestep of the segment's series. In the current pipeline, `run_ts` is the
earliest depth timestamp, so T equals the run time. Older runs stored a different folder time,
which is why the code does not use a folder time as T. All times are the naive
Vietnam local time (UTC+7), the form that the deleted table `flood_road_values` stored.

Event times are sample times, not interpolated threshold crossings. You can reproduce every value
by reading the segment's rows, and the precision equals the timestep spacing, which is 15 minutes
for a `constant_cycle` run.

The following list gives each metric and its value when the event does not happen in the run
window:

- **Time to peak.** The time from T to the first sample with the maximum depth. `peak_at_window_end`
  is true when that sample is the last one, because the real peak can come after the window. If
  the depth is 0 at every timestep, `peak_time`, `peak_depth_m`, `time_to_peak`, and
  `peak_at_window_end` are all NULL.
- **Recession onset.** The first sample after the peak whose depth is below the peak depth. It is
  NULL when the segment is dry or when the depth never drops below the peak in the window.
- **T+1h and T+2h forecast depth.** The depth at T plus 1 hour and T plus 2 hours. If the time
  falls between two samples, the value is a linear interpolation. It is NULL when the time is later
  than the last sample.
- **Passability, per vehicle.** A segment is impassable for a vehicle at any sample where depth is
  at or above that vehicle's hard-block depth. `passability` is one of three values:
  `never_impassable`, `restored`, or `not_restored`.
- **Pre-closure time, per vehicle.** One hour before `closed_at`, the first impassable sample. If
  that hour starts before T, the value is T. It is NULL when `passability` is `never_impassable`.
- **Passability restoration time, per vehicle.** `restored_at` is the first sample after the last
  impassable sample. The last impassable sample matters, not the first, because a segment can close
  again after a short dip. It is NULL when `passability` is `never_impassable` or `not_restored`.

In Python, passability is a small sum type: `NeverImpassable` or `Closed(closed_at,
pre_closure_at, restored_at)`. `CHECK` constraints on `flood_segment_metrics` enforce the same
pairs of NULL and non-NULL columns.

## Vehicle thresholds

`extract_run.impassable_from_m()` reads the thresholds from
`floodmap/graphhopper-flood-road/scripts/flood_utils.py`. It takes the `band_min` of the deepest
band from `depth_bands_m`. `flood_areas.py` uses the same band with `depth >= band_min` to make a
segment impassable for routing. For the values in use, see [[routing-depth-threshold-model]].

## Open items

- The loader SQL and the table script have not run against PostGIS. No local PostGIS server was
  available. The Python tests cover the computation, the grouping of rows into segments, and the
  flattening of metrics into rows.
- Resolved 2026-09-28: `compose.yml` mounts `floodmap/graphhopper-flood-road/scripts` read-only into
  the Airflow containers at `/opt/airflow/floodmap/graphhopper-flood-road/scripts` (`245fe66`), so
  `impassable_from_m()` imports. See [[BL-003-airflow-cannot-import-flood-utils|airflow-cannot-import-flood-utils]].
- The PRD acceptance asks for a non-NULL pre-closure time on every row. That is not possible for a
  vehicle whose threshold the segment never reaches. For those rows, pre-closure time is NULL by
  design.
- The only real sample that was available locally, `flood_road_20260522T103000.geojson` (deleted on
  2026-10-13), had two timesteps with equal depths on every segment. It checked the flat case, but not rising or
  falling depths. The storm test dataset of 58 runs gives real rising and falling depths ([[test-dataset]],
  [[US-127-build-the-history-and-metrics-from-the-restored-road-values|US-127]]).
- The row key changed with [[US-121-read-the-flood-metrics-from-the-edge-table|US-121]]. New rows use `edge_key`, and rows from before keep `segment_key`, which is `md5(ST_AsEWKB(geom_4326))`. The `road_segment` table that this key could have come from was deleted with [[US-123-delete-flood-on-roads-and-flood-road-values|US-123]].
- Run on real data 2026-10-01 (`US-060`): `extract_run.py 20260930T020000` ran inside
  `airflow_new-airflow-worker-1` and wrote 23,324 rows for 5,831 segments and 4 vehicle types in
  about 4 seconds. The segment count equals the run's distinct `geom_4326` values, and
  `peak_depth_m` equals the largest `depth` of the segment for all 5,831. For that run,
  the `segment_id` of the deleted table `flood_road_values` was filled on every row and mapped 1 to 1 to the geometry.

