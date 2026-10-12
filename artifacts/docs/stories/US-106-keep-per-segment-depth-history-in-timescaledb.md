---
date_drafted: 2026-10-10
type: user-story
us_id: "US-106"
title: "Write per-segment depth history to TimescaleDB"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: Reviewed
kind: story
priority: P1
estimate: M
sprint: 14
subsystem: airflow-pipeline, timescaledb
source_ideas: []
related: ["[[timescaledb-schema]]", "[[core-output-contract]]", "[[flood-on-roads]]", "[[US-113-backfill-per-segment-depth-history|US-113]]"]
tags: [user-story]
---

# US-106 Write per-segment depth history to TimescaleDB

As an analyst, I want the depth of each road piece to stay on record after the pipeline prunes its own tables, so I can study past floods.

This is part (a) of the split of the original story.
It covers the table, the write path, and the rules.
The one-time load of the rows that already exist is part (b), [[US-113-backfill-per-segment-depth-history|US-113]].

The design follows [[timescaledb-schema]] and [[decision-log|D-028]], as changed by [[decision-log|D-032]].
[[US-105-decide-what-flood-history-the-industry-apps-need|US-105]] measured the sizing, and [[decision-log|D-032]] sets the grain, the one-year retention, the rule for which run wins, and how a consumer tells dry from unknown.
A new asset `FLOOD_ROAD_VALUES` in `dags/core_assets.py` is emitted by task `flood_on_roads` of `routing_adapter`.
A new DAG `flood_history` runs on that asset and copies the run's per-piece depths into `depth_history`.
The loader converts `forecast_time` (Vietnam time, no offset) to a UTC `valid_time`, writes `cycle` as `constant_cycle`, and keeps the later `issued_at` when two runs cover the same moment.
A piece that the earlier run wets and the winning run does not wet gets depth 0, or loses its earlier row, so the earlier depth does not stay as the answer ([[decision-log|D-032]]).
`flood_history` also writes a `history_moment` table (`valid_time` as primary key, with `issued_at`) for every moment the run covers, even when no piece is wet.
The task runs before the 24-hour prune of `flood_road_values` can remove the run.
The `timescaledb-data` volume stays on C:. The owner decided on 2026-10-12 not to move it to D:, because D: is a hard disk drive and a database needs the speed of the SSD. The history is about 1.3 GB a year compressed ([[decision-log|D-032]]), so it does not repeat [[BL-022-docker-data-vhdx-fills-c-drive-again|BL-022]]. The story records the volume size after the first loads.
`create_timescale_tables.py` runs from the DAG on every run, like `0b_ensure_schema` does for `storage-postgres`.

Given a replay run on the server, when `flood_history` finishes, then `depth_history` has one row per wet road piece and step of that run, a count query on `flood_road_values` for the same run gives the same number, and the hypertable exists on the real TimescaleDB server (`SELECT * FROM timescaledb_information.hypertables`).
Given the same run loaded twice, then the row count does not change.
Given `depth_history` with a compression policy and a drop policy (`timescaledb_information.jobs`), when the owner compresses one chunk of the replay data by hand, then `hypertable_compression_stats` gives the compression ratio of that chunk, and the story records it so [[decision-log|D-028]] can be checked against the estimate of 10 times.
The ratio comes from one hand-compressed chunk, so it is a sample, and it does not show that the scheduled compression job runs.
Given a second run that overlaps the first by one step, then that step keeps the later run's depth.

Answered by the owner on 2026-10-12 ([[decision-log|D-038]]): build this story now. It keys `depth_history` by `segment_id`, and the staged replacement re-keys it on `edge_key` in [[US-122-point-depth-history-at-the-edge-table|US-122]].
The re-key costs one step later. Waiting for [[US-117-export-a-stable-key-with-each-graph-edge|US-117]] and [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]] avoids it but moves the history out of Sprint 13.

Dependencies: [[US-105-decide-what-flood-history-the-industry-apps-need|US-105]] is `Done`.
[[US-113-backfill-per-segment-depth-history|US-113]] depends on this story and is in the same sprint.

## Status history

- **2026-10-10, draft.** Not started: it waits for the decision of `US-105`.
- **2026-10-12, Ready.** Split at Sprint 13 planning into part (a), this story, and part (b), [[US-113-backfill-per-segment-depth-history|US-113]]. The open rule for the winning run is settled by [[decision-log|D-032]], so it is no longer open here. Sized M (3 points).
- **2026-10-12, Ready.** The product owner chose to check compression by hand, on one chunk of the replay data, for the acceptance check.
- **2026-10-12, In progress.** Started after the owner accepted [[decision-log|D-038]]. The build keys `depth_history` by `segment_id`, and [[US-122-point-depth-history-at-the-edge-table|US-122]] re-keys it later.
- **2026-10-12, Reviewed.** Built on `modular`, not pushed and not deployed. The acceptance checks on the server wait for the deploy and for the owner's hand compression of one chunk.
- **2026-10-12, Reviewed, monitoring.** `flood_history` is deployed with no import errors and has never run, because no `routing_adapter` run has emitted `FLOOD_ROAD_VALUES` since the deploy. The owner chose to wait for a real forecast above 5 mm/h and not to trigger `routing_adapter` by hand on the storm run, which would put stale storm data on the live map. The check, the server screenshot, and the acceptance wait for that run.
- **2026-10-12, sprint 14.** Picked for [[SPR-014-finish-the-edge-depth-table-replacement|SPR-014]] at the product owner's request.

- **2026-10-12, Reviewed.** The event-triggered run of `flood_history` passed on the server, with a screenshot (details item 15). Open for `Done`: the compression measurement on more data, and the owner's acceptance.

## Evidence and details

**Evidence:** tests run on a throwaway TimescaleDB 2.30.1 container on the server (removed afterwards), and one real run loaded into it. The server screenshot of the event-triggered run is `artifacts/docs/stories/evidence/us-106-event-run.jpg` (details item 15).

**Details:**

1. `create_timescale_tables.py` gives `depth_history` 7-day chunks, compression per closed chunk, and a 365-day drop policy, and adds `history_moment` with the same chunks and drop policy. Running the script twice changes nothing. A table-wide advisory lock covers the two callers, `0b_ensure_schema` and `flood_history`.
2. `history_moment` is a hypertable and not a plain table, so an old moment is forgotten together with its depths. A plain table would keep moments after their depths were dropped, and those old moments would read as dry.
3. `scripts/flood_history/load_run.py` holds the write rule as one pure function, `plan_write`, with the I/O around it. The lock is table-wide, because two different runs that share a moment could otherwise both read `history_moment` before either writes.
4. The DAG `flood_history` runs on the asset `FLOOD_ROAD_VALUES`. When the scheduler folds several events into one run, it loads every run of them, oldest first, so no run leaves its early moments unknown. A manual run loads the newest published run.
5. The tests pass: 18 DB tests (`scripts/database/test_create_timescale_tables.py` and `scripts/flood_history/test_load_run.py`) against the throwaway TimescaleDB, and 8 in `test/test_flood_history_dag.py`, 28 in `test/test_routing_adapter_dag.py`, and 19 in `test/test_flood_mapping_dag_graph.py` without a database.
6. The 18 DB tests also passed on 2026-10-12 inside `airflow_new-airflow-worker-1`, against the real server TimescaleDB (`timescaledb`, database `flood_metrics`), with files copied into a temporary folder that was removed afterwards. Each test works in its own schema, which it drops. A check afterwards found no test schema and no test job, and `public.history_moment` does not exist yet, so the real tables were untouched.
7. Real data, run `20261011T001500` copied from the server's read-only tables into the throwaway database: 19,792 rows loaded, equal to the count of the run in `flood_road_values`, over 8 moments, with 8 rows in `history_moment`. A second load gave the same counts. The first moment, 00:15 +07, is stored as 17:15 UTC.
8. The volume `timescaledb-data` stays on C: (owner decision of 2026-10-12, hard disk drive on D:).
9. Server, 2026-10-12, run by the owner after the pull of `modular` (server head `b370a09`): `depth_history` holds 19,792 rows over 8 moments and 2,474 segments (14,135 rows with a depth above 0), and `history_moment` holds 8 rows. This equals the 19,792 rows that run `20261011T001500` has in `flood_road_values`.
10. Server, same day: the owner compressed the one chunk by hand (`_hyper_3_19_chunk`, 2026-10-08 to 2026-10-15). `hypertable_compression_stats` gives 3,022,848 bytes before and 1,761,280 bytes after, a ratio of 1.7. The jobs `policy_compression` (1008) and `policy_retention` (1009) exist for `depth_history`, and `policy_retention` (1010) for `history_moment`.
11. The ratio of 1.7 is far below the 11.4 that [[decision-log|D-028]] and [[decision-log|D-032]] expect, and D-028 says to revisit when compression is far below 10 times. The sample does not decide this: the chunk holds one run, so each segment has at most 8 rows to pack, and the 11.4 came from 319,573 rows over three days. The ratio is measured again on more data, after [[US-113-backfill-per-segment-depth-history|US-113]] loads the retained runs or after a day of real runs. The owner reads the number then.
12. The DAG `flood_history` is registered in Airflow and unpaused (`airflow dags list`, 2026-10-12, about 5 minutes after the file reached the server, which is the scan interval for new files). No import error. No real run had emitted `FLOOD_ROAD_VALUES` since the deploy and no rain above 5 mm/h was forecast, so item 14 made the event by hand.
13. Open for `Done`: the later measurement of item 11, and the owner's acceptance. The server screenshot and the event-triggered run are in item 15.
14. For [[US-122-point-depth-history-at-the-edge-table|US-122]]: the table is keyed by `segment_id`, and the loader reads `flood_road_values`, so both change there.
15. Server, 2026-10-12 16:58 +07: the event-triggered run. A `flood_road_values` asset event (id 177, `run_ts` `20261011T001500`) was created by hand through the Airflow API, because no real run had emitted one. It started the run `asset_triggered__2026-10-12T09:58:29.640589+00:00_dWSONnac` of `flood_history`, and the task `load_depth_history` succeeded in 2 seconds: "8 moments written, 0 skipped for a later run, 19792 rows". `depth_history` still holds 19,792 rows and `history_moment` 8, so the load is idempotent. The screenshot is `us-106-event-run.jpg` and the captured output is `us-106-event-run-output.txt`. The first run emitted by `routing_adapter` itself is not tested yet, but its event has the same asset and the same `run_ts` extra.
