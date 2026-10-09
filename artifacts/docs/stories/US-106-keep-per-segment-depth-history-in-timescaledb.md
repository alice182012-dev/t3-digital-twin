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

The default design follows [[timescaledb-schema]] and changes if [[US-105-decide-what-flood-history-the-industry-apps-need|US-105]] decides otherwise.
A new asset `FLOOD_ROAD_VALUES` in `dags/core_assets.py` is emitted by task `flood_on_roads` of `routing_adapter`.
A new DAG `flood_history` runs on that asset and copies the run's per-piece depths into `depth_history`.
The loader converts `forecast_time` (Vietnam time, no offset) to a UTC `valid_time`, writes `cycle` as `constant_cycle`, and keeps the row with the later `issued_at` when two runs cover the same moment.
The task runs before the 24-hour prune of `flood_road_values` can remove the run.
`create_timescale_tables.py` runs from the DAG on every run, like `0b_ensure_schema` does for `storage-postgres`.

Given a replay run on the server, when `flood_history` finishes, then `depth_history` has one row per wet road piece and step of that run, a count query on `flood_road_values` for the same run gives the same number, and the hypertable exists on the real TimescaleDB server (`SELECT * FROM timescaledb_information.hypertables`).
Given the same run loaded twice, then the row count does not change.
Given a second run that overlaps the first by one step, then that step keeps the later run's depth.

Dependencies: US-105.

## Status history

- **2026-10-10, draft.** Not started: it waits for the decision of `US-105`.

## Evidence and details

Fill this when the story reaches `Done`.
A server screenshot of the three queries is the evidence.
