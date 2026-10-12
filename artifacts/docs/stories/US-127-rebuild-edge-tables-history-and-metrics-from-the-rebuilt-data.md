---
date_drafted: 2026-10-12
type: user-story
us_id: "US-127"
title: "Rebuild edge tables, history, and metrics from the rebuilt data"
epic: "[[EP-22-keep-a-real-storm-as-the-test-dataset]]"
status: Not started
kind: story
priority: P2
estimate: M
sprint: 
subsystem: testing, flood-data
source_ideas: []
related: ["[[test-dataset]]", "[[decision-log|D-039]]"]
tags: [user-story]
---

# US-127 Rebuild edge tables, history, and metrics from the rebuilt data

As a developer, I want the edge depth tables, the depth history, and the flood metrics of the storm built into the test databases, so every consumer of the pipeline output has real data.

The script builds the 58 edge depth files (`build_edge_depth`), loads `depth_history` and `history_moment` with `load_run` of [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]], and runs `extract_run` for `flood_segment_metrics`.
It then measures the compression ratio of `depth_history` on the full storm, which answers the open item of [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]].

Given the road values of a run in the test database, when the edge table is built, then it equals the snapshot file of that run byte for byte, or the story lists the differences and their cause.
Given the 58 runs loaded, then `history_moment` has the moments of the storm and `hypertable_compression_stats` gives a ratio, which the story records.

Dependencies: [[US-126-rebuild-the-raster-tiles-and-road-values-from-the-netcdf|US-126]] is `Done`, and [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]] is `Done`.

## Status history

- **2026-10-12, draft.** Raised with [[decision-log|D-039]].

## Evidence and details

Fill this when the story reaches `Done`.
