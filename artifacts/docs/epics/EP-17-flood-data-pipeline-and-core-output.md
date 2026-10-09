---
date_drafted: 2026-10-10
type: epic
epic_id: "EP-17"
theme: flood-data
status: active
subsystem: airflow-pipeline, core-output, storage
tags: [epic, flood-data, pipeline]
related: ["[[PRD-002-t3-digital-twin-architecture-gaps|archived PRD-002]]", "[[minio-flood-extent-pipeline]]", "[[raster-first-flood-pipeline]]", "[[core-output-contract]]", "[[rain-replay-test-environment]]", "[[3di-simulation-orchestration]]", "[[decision-log]]"]
---

# EP-17 Flood data pipeline and core output

## Goal

The Airflow pipeline turns each 3Di simulation into the stored data that every consumer reads: depth rasters, flood-extent polygons, per-road values, flood metrics, and the archive of a run. A rain replay on the server tests the pipeline against a known storm.

## Why

The architecture design called for a metric extractor, point-depth lookup, a route-forecast query, and time-series storage, and the repository had none of them (the gap analysis is in the archived [[PRD-002-t3-digital-twin-architecture-gaps|PRD-002]]). Later work added limits that the pipeline must keep: runs must finish inside the 15-minute cycle, old rows must be pruned, and the disk must not fill again ([[BL-022-docker-data-vhdx-fills-c-drive-again|BL-022]]).

## Dependencies and assumptions

- The pipeline reads `calculate_depth.py` output. The depth statistic is the maximum depth ([[decision-log|D-006]]).
- `background_cycle` runs and the 24-bar histogram were dropped on 2026-10-01 ([[decision-log|D-009]]).
- The five netcdf tables were dropped on 2026-10-10 ([[decision-log|D-022]]).
- Test points stay inside the model border (`.claude/CLAUDE.md`).

## Definition of done

Run each check on the server.

1. Given a completed `constant_cycle` run, when the metric extractor runs, then each road segment and vehicle type has a time-to-peak, a pre-closure time, and a T+1h forecast depth, and one spot-checked segment matches a hand computation from the raw rasters.
2. Given a loaded `depth.tif`, when `GET /flood/points` is called inside the flooded extent, then the depth equals the value `gdallocationinfo` reads at that pixel.
3. Given a route that crosses flooded roads, when the route-forecast query runs, then it returns one average depth for each 30-minute bucket, and one spot-checked bucket matches a hand computation from `flood_road_values`.
4. Given the 48-hour replay, when the storm ends, then storage is inside its limit and every run finished inside the 15-minute cycle.

## Risks and open questions

- Rate of growth of `9c` within a chain is unexplained ([[BL-023-9c-sampling-step-runs-over-770-seconds|BL-023]], `monitoring`).
- The rain gate stopped simulation while the flood still stood ([[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands|BL-028]], P0, fixed in code by `US-101`, resolves after a full-storm replay).
- Archiving a run needs real rain above 5 mm/h ([[US-094-archive-results-3di-nc-and-a-run|US-094]]).

## Stories

```dataview
TABLE title AS "Story", kind AS "Kind", sprint AS "Sprint", priority AS "Priority", estimate AS "Estimate", status AS "Status"
FROM "docs/stories"
WHERE contains(string(epic), "EP-17")
SORT file.name ASC
```

## Status history

- **2026-10-10, active.** Created from the Scrum adoption ([[decision-log|D-024]]). It merges the archived epics `EP-03`, `EP-04`, `EP-06`, `EP-12`, `EP-13`, and `EP-15`, and takes the pipeline stories of `EP-07`. Story history lines stay in [[EP-04-timescaledb-and-flood-metrics-history|the archived histories]].
