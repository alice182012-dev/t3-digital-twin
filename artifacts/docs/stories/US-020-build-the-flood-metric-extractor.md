---
date_drafted: 2026-09-23
type: user-story
us_id: "US-020"
story_label: "3"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Done
priority: P1
estimate: L
sprint: 4
subsystem: architecture-backend
related: ["[[EP-04-timescaledb-and-flood-metrics]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Build the flood metric extractor"
---

# US-020 Build the flood metric extractor

As a downstream consumer (internal reporting, or a future endpoint), I want time-to-peak, recession onset, per-vehicle passability restoration time, T+1h and T+2h forecast depth, and pre-closure time computed per road segment per vehicle type, so real flood-impact metrics exist instead of raw depth rasters alone.
Given a completed `constant_cycle` run with at least 2 depth timesteps in `flood_road_values`, when the metric extractor runs against that run's `run_ts`, then querying its output table returns a row per road segment per vehicle type with a non-null time-to-peak, pre-closure time, and T+1h forecast depth, matching the values computable by hand from the same run's raw depth rasters for one spot-checked segment.
Dependencies: None (reads `calculate_depth.py`'s output directly, independent of TimescaleDB).
Evidence: ![[us-060-extractor-check-output.png|700]]
Details:
1. What: the flood metric extractor, covered by 19 unit tests.
   It computes time to peak, recession onset, passability restoration, T+1h and T+2h depth, and pre-closure time per road segment and vehicle type.
2. How: `metrics.py` computes one segment's metrics from its depth series, and `extract_run.py` reads a run from `flood_road_values` and writes `flood_segment_metrics`.
   It ran in the Airflow worker on the 2026-09-30 02:00:00 run (Story 5).
3. Why: real flood-impact metrics instead of raw depth rasters alone.
4. Effect: the loader and writer SQL work on real data.
   46,648 rows became 23,324 metric rows in about 4 seconds.
   The row key is still `md5(ST_AsEWKB(geom_4326))`.
   `flood_road_values.segment_id` is filled for every row of the run and maps 1 to 1 to the geometry (5,831 each), so Story 4 can switch the key to `segment_id` without changing the segment count.
   No DAG task runs the extractor yet.
