---
date_drafted: 2026-10-10
type: user-story
us_id: "US-106"
title: "Write per-segment depth history to TimescaleDB"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: Ready
kind: story
priority: P1
estimate: M
sprint: 13
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
The `timescaledb-data` volume moves to a host path on D: before the first load, as `airflow-logs` already does in `compose.yml`, because C: holds Docker's disk image ([[BL-022-docker-data-vhdx-fills-c-drive-again|BL-022]]).
`create_timescale_tables.py` runs from the DAG on every run, like `0b_ensure_schema` does for `storage-postgres`.

Given a replay run on the server, when `flood_history` finishes, then `depth_history` has one row per wet road piece and step of that run, a count query on `flood_road_values` for the same run gives the same number, and the hypertable exists on the real TimescaleDB server (`SELECT * FROM timescaledb_information.hypertables`).
Given the same run loaded twice, then the row count does not change.
Given `depth_history` with a compression policy and a drop policy (`timescaledb_information.jobs`), when the owner compresses one chunk of the replay data by hand, then `hypertable_compression_stats` gives the compression ratio of that chunk, and the story records it so [[decision-log|D-028]] can be checked against the estimate of 10 times.
The ratio comes from one hand-compressed chunk, so it is a sample, and it does not show that the scheduled compression job runs.
Given a second run that overlaps the first by one step, then that step keeps the later run's depth.

Dependencies: [[US-105-decide-what-flood-history-the-industry-apps-need|US-105]] is `Done`.
[[US-113-backfill-per-segment-depth-history|US-113]] depends on this story and is in the same sprint.

## Status history

- **2026-10-10, draft.** Not started: it waits for the decision of `US-105`.
- **2026-10-12, Ready.** Split at Sprint 13 planning into part (a), this story, and part (b), [[US-113-backfill-per-segment-depth-history|US-113]]. The open rule for the winning run is settled by [[decision-log|D-032]], so it is no longer open here. Sized M (3 points).
- **2026-10-12, Ready.** The product owner chose to check compression by hand, on one chunk of the replay data, for the acceptance check.

## Evidence and details

Fill this when the story reaches `Done`.
A server screenshot of the three queries is the evidence.
