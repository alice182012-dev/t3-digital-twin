---
date_drafted: 2026-10-10
type: epic
epic_id: "EP-21"
theme: flood-data
status: active
subsystem: analysis, core-output, storage, timescaledb
tags: [epic, flood-data, analysis, consumers]
related: ["[[EP-17-flood-data-pipeline-and-core-output]]", "[[EP-18-time-aware-routing-engine]]", "[[core-output-contract]]", "[[timescaledb-schema]]", "[[flood-metric-extractor]]", "[[architecture-block-diagram]]", "[[decision-log]]"]
---

# EP-21 Industry analysis on the flood data

## Goal

Applications for different industries read the forecast flood data and the flood history from one published contract, and each runs its own analysis.
Routing ([[EP-18-time-aware-routing-engine|EP-18]]) is the first such application.
A flood-data-analysis application is the second.
Every further industry is a new consumer of the same contract, not a change to the pipeline.
This epic prepares the platform for finance, urban planning, and agriculture. It builds no application for them, so a customer from any industry can start quickly.

## Why

A second consumer cannot be added cleanly today.
The facts below were read from the code and the contract on the branch `modular` on 2026-10-10.

- The pipeline keeps the newest 8 runs of the raster, polygon, and step tables, 24 hours of `flood_road_values`, and 3 edge depth files ([[core-output-contract]], "Retention"). An analysis of past floods has nothing to read.
- The planned history store, the `depth_history` table in TimescaleDB, has no writer. Its `create_hypertable` calls have never run against a real TimescaleDB server ([[timescaledb-schema]], "Open items").
- The only read-only role is `routing_reader`. `scripts/database/create_routing_reader_role.py` creates that one role from the whole contract page.
- A consumer outside Airflow has no single signal that a run is complete. It checks `flood_extent_step`, the tile table, and `flood_road_values` separately.
- The Airflow image holds GDAL 3.6.2, GRASS, Chrome, and tesseract. Libraries for a new consumer would go into that image through `requirements.txt` unless the consumer has its own container.
- `storage-backend` (Django migrations) and the pipeline DDL scripts both write to the database `minio_custom`, in schema `public`.

## Dependencies and assumptions

- Proposed, not decided. An industry application is a read-only consumer of the contract tables. It writes only to its own schema. The pipeline stays the only writer of the contract tables. [[US-105-decide-what-flood-history-the-industry-apps-need|US-105]] ends with the decision that confirms or changes this.
- A run forecasts about the next 2 hours (`SIMULATION_DURATION` 7200 s) and a run starts every 15 minutes (`UPDATE_INTERVAL` 900 s, `compose.yml`). A moment in time therefore has several forecasts, one per run that covers it.
- [[decision-log|D-028]] keeps the latest forecast of each road piece and moment for several years, and no other forecast.
- No gauge observations enter the pipeline. The gauge hot start is designed and not built ([[architecture-block-diagram]]). In this epic, history means the model's own forecast values.
- `flood_road_values` has no row for a road piece that was dry at every step of a run ([[core-output-contract]]). A missing row is not proof that the piece was dry at that time.
- Size reference. After the first prune on 2026-10-09 the table held 1,087,512 rows for 45 runs, about 24,000 rows per run. A day has at most 96 runs.
- The extractor `scripts/flood_metrics/extract_run.py` stays in [[EP-17-flood-data-pipeline-and-core-output|EP-17]]. An analysis can read its output table `flood_segment_metrics` once that story schedules it.
- A test point of any story stays inside the model border (`.claude/CLAUDE.md`).

## Definition of done

Run each check on the server.

1. Given a replay run published on the server, when an application connects with its own read-only role, then it reads the run's manifest rows and the run's `flood_road_values`, and a write, or a read of a table outside its list, fails with a permission error.
2. Given a run older than the retention limit of the contract tables, when the application asks for the depth of one road piece at a time inside that run, then it gets the value from the history store, and a spot check against the `flood_road_values` rows loaded at that time gives the same number.
3. Given the analysis service in its own container, when the image is built, then it installs no package into the Airflow image.
4. The check for a first industry analysis is written when a customer asks for one. This epic does not build it.

## Risks and open questions

- Finance and agriculture may ask about parcels and fields, which the road-piece history of [[decision-log|D-028]] does not answer. A new story adds an area-based history when a customer needs it.
- History from the model's forecast is not history of what happened. An analysis that needs observed depth waits for the gauge work.
- Storage growth is unmeasured. No compression or retention policy exists for the Timescale tables.

## Stories

```dataview
TABLE title AS "Story", kind AS "Kind", sprint AS "Sprint", priority AS "Priority", estimate AS "Estimate", status AS "Status"
FROM "docs/stories"
WHERE contains(string(epic), "EP-21")
SORT file.name ASC
```

## Status history

- **2026-10-10, active.** Created after the review of how modular the system is. Stories `US-105` to `US-110` are added to the backlog with no sprint.
