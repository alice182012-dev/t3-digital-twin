---
date: 2026-09-23
type: concept
status: active
tags: [flood-metrics, postgis, sprint-2]
related: ["[[timescaledb-and-flood-metrics]]", "[[t3-digital-twin-architecture-gaps]]", "[[T3-Digital-Twin_Architecture]]", "[[routing-depth-threshold-model]]", "[[timescaledb-schema]]"]
last_updated: 2026-09-23
---

# Flood metric extractor

The flood metric extractor turns one run's per-segment depth series into flood-impact metrics for
each road segment and vehicle type. It is Story 3 of [[timescaledb-and-flood-metrics]], and it
implements the metrics that section 4.4 of [[T3-Digital-Twin_Architecture]] lists. No DAG task
runs it yet.

## Code and data flow

- `scripts/flood_metrics/metrics.py` holds the computation. `extract(series, impassable_from_m)`
  is a pure function. It takes a `DepthSeries` (timestamps and depths in metres) and a map from
  vehicle type to hard-block depth, and it returns a `SegmentMetrics`.
- `scripts/flood_metrics/extract_run.py` is the shell around `extract`. It reads one run from
  `flood_road_values`, groups the rows into one series per segment, and writes the results.
- `scripts/database/create_flood_metrics_tables.py` creates the output table,
  `flood_segment_metrics`, in `storage-postgres`. The script is idempotent.

To extract one run, run the table script once, then run `python
scripts/flood_metrics/extract_run.py RUN_TS`, where `RUN_TS` is the run folder name, such as
`20260923T100000`. The loader selects `flood_road_values` rows whose `timestamp` equals that
value. The writer deletes the run's earlier rows and inserts the new rows in one transaction, so a
rerun replaces the earlier result.

The output table lives in `storage-postgres` instead of TimescaleDB, so the extractor works
without the TimescaleDB service. Story 4 copies from `flood_segment_metrics` into TimescaleDB.

## Segment key

`flood_road_values` has no segment ID, and `road_name` repeats across one road's segments. In the
`20260522T103000` sample, `way/601864287` has 12 segments. `build_rows` in
`scripts/database/geojson_to_pg.py` writes one row per feature per timestep and repeats the
feature's geometry on each row. Equal geometry therefore identifies one segment, and the extractor
uses `md5(ST_AsEWKB(geom_4326))` as `segment_key`. A later loader can join back to
`flood_road_values` with the same expression. The table is unique on `(run_ts, segment_key,
vehicle_type)`.

## Metric definitions

"T" is the first timestep of the segment's series. In the current pipeline, `run_ts` is the
earliest depth timestamp, so T equals the run time. Older runs stored a different folder time,
which is why the code does not use `flood_road_values.timestamp` as T. All times are the naive
Vietnam local time that `flood_road_values.forecast_time` stores.

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
- The Airflow containers mount `./scripts` but not `./floodmap`, so `impassable_from_m()` fails
  inside Airflow. Before a DAG task calls the extractor, mount
  `floodmap/graphhopper-flood-road/scripts` into the container, or move `flood_utils.py` to a
  path that both the backend and Airflow can import.
- The PRD acceptance asks for a non-NULL pre-closure time on every row. That is not possible for a
  vehicle whose threshold the segment never reaches. For those rows, pre-closure time is NULL by
  design.
- The only real sample available locally, `flood_road_20260522T103000.geojson`, has two
  timesteps with equal depths on every segment. It checks the flat case, but not rising or falling
  depths. A 25-timestep `constant_cycle` run is still needed for a real check of those cases.
