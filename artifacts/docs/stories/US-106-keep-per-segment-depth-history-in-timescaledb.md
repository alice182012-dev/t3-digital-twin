---
date_drafted: 2026-10-10
type: user-story
us_id: "US-106"
title: "Keep per-segment depth history in TimescaleDB"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: Not started
kind: story
priority: P1
estimate: M
sprint: 
subsystem: airflow-pipeline, timescaledb
source_ideas: []
related: ["[[timescaledb-schema]]", "[[core-output-contract]]", "[[flood-on-roads]]"]
tags: [user-story]
---

# US-106 Keep per-segment depth history in TimescaleDB

As an analyst, I want the depth of each road piece to stay on record after the pipeline prunes its own tables, so I can study past floods.

The design follows [[timescaledb-schema]] and [[decision-log|D-028]], as changed by [[decision-log|D-032]].
[[US-105-decide-what-flood-history-the-industry-apps-need|US-105]] measured the sizing, and [[decision-log|D-032]] sets the grain, the one-year retention, and how a consumer tells dry from unknown.
A new asset `FLOOD_ROAD_VALUES` in `dags/core_assets.py` is emitted by task `flood_on_roads` of `routing_adapter`.
A new DAG `flood_history` runs on that asset and copies the run's per-piece depths into `depth_history`.
The loader converts `forecast_time` (Vietnam time, no offset) to a UTC `valid_time`, writes `cycle` as `constant_cycle`, and keeps the row with the later `issued_at` when two runs cover the same moment.
`flood_history` also writes a `history_moment` table (`valid_time` as primary key, with `issued_at`) for every moment the run covers, even when no piece is wet.
Open point: settle which run wins when the later run wets no piece, because `flood_on_roads.py` picks the newest run with rows and [[decision-log|D-032]] picks the later run that covers the moment.
The task runs before the 24-hour prune of `flood_road_values` can remove the run.
The `timescaledb-data` volume moves to a host path on D: before the first load, as `airflow-logs` already does in `compose.yml`, because C: holds Docker's disk image ([[BL-022-docker-data-vhdx-fills-c-drive-again|BL-022]]).
`create_timescale_tables.py` runs from the DAG on every run, like `0b_ensure_schema` does for `storage-postgres`.

Given a replay run on the server, when `flood_history` finishes, then `depth_history` has one row per wet road piece and step of that run, a count query on `flood_road_values` for the same run gives the same number, and the hypertable exists on the real TimescaleDB server (`SELECT * FROM timescaledb_information.hypertables`).
Given the same run loaded twice, then the row count does not change.
Given `depth_history` with a compression policy and a drop policy (`timescaledb_information.jobs`), when the compression job has run on the replay data, then `hypertable_compression_stats` gives the real compression ratio, and the story records it so [[decision-log|D-028]] can be checked against the estimate of 10 times.
Given a second run that overlaps the first by one step, then that step keeps the later run's depth.

Dependencies: US-105.

## Status history

- **2026-10-10, draft.** Not started: it waits for the decision of `US-105`.

## Evidence and details

Fill this when the story reaches `Done`.
A server screenshot of the three queries is the evidence.
