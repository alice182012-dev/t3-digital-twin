---
date_drafted: 2026-10-12
type: user-story
us_id: "US-118"
title: "Write the edge depth to a queryable table"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: Done
kind: story
priority: P1
estimate: M
sprint: 14
subsystem: routing, flood-data, core-output
source_ideas: []
related: ["[[decision-log|D-038]]", "[[US-115-decide-whether-the-edge-depth-table-replaces-flood-road-values|US-115]]"]
tags: [user-story]
---

# US-118 Write the edge depth to a queryable table

As the owner of the flood data, I want the edge depth build to also write its wet edges to a queryable table with a run registry, so one sampler serves the engine, the map, the metrics, and the history.

Task `9c_build_edge_depth_table` already samples every edge at every step and writes the binary table for the engine.
This story makes the same pass write the rows of wet edges (`edge_key`, run, forecast time, depth in cm) to a table, and one registry row per run that holds the run's forecast times, including a run with no wet edge.
The story decides the database (`storage-postgres` or TimescaleDB) and the retention, and it measures the added time of `9c` against its 5-minute limit ([[BL-023-9c-sampling-step-runs-over-770-seconds|BL-023]]).

Given a replay run, when `9c` ends, then the table has one row per wet edge and step, the count matches the `wet_edges` that `9c` reports, and the registry has one row for the run with its forecast times.
Given a run with no wet edge, then the registry has a row for the run and the table has none for it.
Given the same run built twice, then the row count does not change.
Given 50 consecutive runs on the server, then the longest `9c` stays under 150 s, the revisit trigger of [[decision-log|D-038]].

Dependencies: [[US-117-export-a-stable-key-with-each-graph-edge|US-117]] is `Done`. [[US-116-let-a-run-with-no-wet-road-piece-win-the-winner-query|US-116]] is `Done`, or this story includes its registry.

## Status history

- **2026-10-12, draft.** Split from [[decision-log|D-038]], which replaces `flood_road_values` with the edge depth table in stages. It stays in the backlog until the owner accepts the decision.
- **2026-10-12, In progress.** Started on the owner's request, outside the sprint plan, so it has no `sprint`. [[US-117-export-a-stable-key-with-each-graph-edge|US-117]] is `Done`, so `graph_edge.edge_key` exists. The design before the code:
  1. The database is `storage-postgres`, next to `flood_road_values` and `graph_edge`, because the map overlay and the route fallback read it there through the routing reader role ([[US-119-read-the-map-overlay-and-route-fallback-from-the-edge-table|US-119]]). The history stays in TimescaleDB ([[US-122-point-depth-history-at-the-edge-table|US-122]] re-keys it).
  2. `edge_depth_run` is the registry: `run_ts` (primary key), `graph_hash`, `valid_times` (the run's forecast times, as in `flood_road_file.forecast_times`), and `built_at`. A run with no wet edge has a row here and no rows below.
  3. `edge_depth` holds one row per wet edge and step: `run_ts`, `valid_time_utc`, `edge_key`, `depth_cm` (integer, since the table holds up to 65,535). Its primary key is `(run_ts, valid_time_utc, edge_key)`, and a row goes with its run.
  4. Retention is the 24 hours before the newest run, as for `flood_road_values` ([[decision-log|D-017]]), set by `EDGE_DEPTH_KEEP_HOURS`.
  5. `9c` writes the rows in one transaction before it writes the file and publishes, so a database failure leaves no file and no new `latest`. A rebuild of one run replaces its rows.
- **2026-10-12, In progress.** Built and tested, not deployed. `9c` writes the rows and the registry before the file (commit "Write the wet edges of each run to edge_depth with a run registry"), and 135 `edge_depth` tests pass against the real PostGIS. The added time was measured on the 8 stored storm runs (details item 2). The server does not have the code yet. Still open: push and pull, the first real `9c` run with the tables, and the check over 50 consecutive runs.
- **2026-10-12, In progress.** Pushed and pulled on the server (`--ff-only` from `alice`, head `10338a4`). `create_edge_depth_tables.py` was run by hand, so `edge_depth_run` and `edge_depth` exist and are empty, and a `routing_adapter` run before the next `flood_mapping_full` run cannot fail on a missing table. Airflow has no import errors and `check_tables.py` reports `FRESH`. The next real `9c` run writes the first rows. `EDGE_DEPTH_KEEP_HOURS` is in `compose.yml` and reaches the containers when they are recreated, and the code default is the same 24.
- **2026-10-12, In progress.** While testing [[US-119-read-the-map-overlay-and-route-fallback-from-the-edge-table|US-119]], `build_edge_depth.py` wrote live rows for two stored storm runs by hand, without `--publish`. Still open: the first real `9c` run that writes rows, and the check over 50 consecutive runs.
- **2026-10-12, sprint 14.** Picked for [[SPR-014-finish-the-remaining-backend|SPR-014]] at the product owner's request.
- **2026-10-12, In progress.** Task `9c_build_edge_depth_table` ran inside `routing_adapter` for the first time, on the hand-made `9b` event of the US-106 test (see [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]], details item 16). It built run `20261011T001500` in 49.3 s and wrote 16,370 rows to `edge_depth` in 0.45 s, as the same run had by hand. `latest` stayed on that file. Still open: a `9c` run on a real simulation, and the check over 50 consecutive runs.
- **2026-10-12, In progress.** Task `9c` now also reads `demo_pin` and passes the pinned run's table to the publish step, so the retention of the edge depth files keeps it ([[US-129-pin-the-peak-step-of-the-demo-flood|US-129]]). The prune of `edge_depth` rows keeps the pinned run too.
- **2026-10-13, In progress.** The first `9c` run on a real simulation happened: the slot 03:30 UTC ran a real 3Di simulation (sim 452776, forecast 0 mm/h through the standing-flood rule), and `9c` built run `20261013T104500` in 24.2 s with 1,219 rows in `edge_depth`. The owner approved the check over 50 consecutive runs on the test dataset. It runs in the worker against `minio_custom_test` (the first 50 runs of the manifest, tiles from the NetCDF, then `build_edge_depth.py`, with the tiles deleted after each run). The first two runs took 43.7 s and 48.9 s to build, and about 5 minutes each to rebuild the tiles, so the loop needs about 6 minutes per run. The log is `data/mapping/testdata_rebuild/run50.log` in the worker, and the loop started at 04:07 UTC and should end at about 09:15 UTC.
- **2026-10-13, In progress.** The check over 50 consecutive runs ended with no failure. The longest `9c` build is 79.5 s, against the limit of 150 s (details item 7). The owner has not accepted the story.
- **2026-10-13, Done.** The product owner accepted it. The criteria of the story are met: the rows and the registry of a replay run (US-118 tests and the server run of 2026-10-12), the run with no wet edge, the second build with the same rows, and 50 consecutive runs with the longest `9c` build at 79.5 s (details item 7). Two real runs on the server confirm the task: the run of 03:30 UTC (24.2 s) and the run of 09:45 UTC (25 s from `9b` to the end of `9c`).

## Evidence and details

**Evidence:** the measurement of 2026-10-12 on the server, from `marie-curie/us-118/measure_rows.py`, with the raw numbers in `marie-curie/us-118/results.json`. It ran from a copy of the new scripts in the worker's `/tmp`, against the live `flood_depth_raster_tile` and the live export, with its own scratch schema `us118` and folder. The schema and the folder are removed. The live tables and the live folder of tables were not touched. There is no screenshot yet, because the code is not deployed.

**Details:**

1. The tests: `test_edge_depth_rows.py` (12 tests) and the new tests of `test_build_edge_depth.py` cover the three criteria that need no live run. The rows of each step carry their keys, the count equals the `wet_edges` of the build, a run with no wet edge is a registry row with no rows, and the same run built twice keeps the row count. They also cover a failed database write leaving no file, an export before format 3 refused, and the 24-hour window.
2. The added time, on the 8 stored storm runs of 2026-10-10 and 2026-10-11 (8 steps each):

   | Run | Whole build (s) | Row write (s) | Rows | Wet edges, sum over 8 steps |
   | --- | --- | --- | --- | --- |
   | `20261010T211500` | 60.7 | 0.57 | 21,746 | 21,746 |
   | `20261010T213000` | 59.0 | 0.54 | 21,923 | 21,923 |
   | `20261010T214500` | 58.7 | 0.51 | 21,895 | 21,895 |
   | `20261010T220000` | 58.5 | 0.51 | 21,719 | 21,719 |
   | `20261010T221500` | 57.9 | 0.53 | 21,412 | 21,412 |
   | `20261010T223000` | 58.2 | 0.56 | 20,989 | 20,989 |
   | `20261011T000000` | 44.6 | 0.34 | 13,650 | 13,650 |
   | `20261011T001500` | 49.0 | 0.46 | 16,370 | 16,370 |

   The row write, which includes the key lookup, adds 0.34 to 0.57 s to a build of 44.6 to 60.7 s, so less than 1 percent. The longest build of this sample is 60.7 s, under the 150 s limit of [[decision-log|D-038]]. Those builds ran on an idle database, so the check over 50 real runs is still open.
3. The counts agree: 8 registry rows, 159,704 rows, equal to the sum of the rows written. A second build of the last run wrote the same 16,370 rows and left 8 registry rows.
4. The size of the table: a run holds 13,650 to 21,746 rows, the same order as `flood_road_values` (about 20,000 per run), so 96 runs a day is about 2 million rows.
5. The first build of a run in the new tables needs `0b_ensure_schema` to have created them. `0b` runs on each `flood_mapping_full` run, and `create_edge_depth_tables.py` can run by hand first, as for `graph_edge`.
6. A flaky test was fixed on the way: `test_real_rain_archives_the_file_and_the_record` read the real free space of the disk and failed on a Mac with under 50 GB free.
7. The check over 50 consecutive runs, on the test dataset in the worker (`minio_custom_test`), from 04:07 to 09:13 UTC on 2026-10-13. The loop took the first 50 runs of the manifest (`20261010T041500` to `20261010T163000`). For each run it rebuilt the tiles from the NetCDF with `rebuild_tiles.py`, ran `build_edge_depth.py` (the build of task `9c`, with the write of the rows), and deleted the tiles. The log is `data/mapping/testdata_rebuild/run50.log` in the worker.
   No run failed. The build took 43.7 s at the shortest, 69.9 s on average (median 71.5 s), and 79.5 s at the longest (run `20261010T154500`), which leaves 70.5 s under the limit of 150 s of [[decision-log|D-038]]. The tile rebuild took 296 s on average and 325 s at most.
   The build time rose from 52.3 s (mean of the first 5 runs) to 77.9 s (mean of the last 5), because the test database keeps the rows of every run (1,514,617 rows of `edge_depth` after 50 runs). Production keeps 24 hours, so this figure is an upper bound.
   The production tables did not change: `edge_depth_run` in `minio_custom` lists the two runs it listed before (`20261011T001500` and `20261013T104500`) and none of the 50 runs. The scratch runs wrote no `latest` file, because the loop does not publish.
