---
date_drafted: 2026-10-12
type: user-story
us_id: "US-127"
title: "Build the history and metrics from the restored road values"
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

# US-127 Build the history and metrics from the restored road values

As a developer, I want the depth history and the flood metrics of the storm built into the test databases from the restored road values, so every consumer of the pipeline output has real data.

The edge depth files and the road values are in the snapshot.
The script loads `depth_history` and `history_moment` with `load_run` of [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]], and runs `extract_run` for `flood_segment_metrics`.
It then measures the compression ratio of `depth_history` on the full storm, which answers the open item of [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]].

Given the 58 runs loaded, then `history_moment` has the moments of the storm and `hypertable_compression_stats` gives a ratio, which the story records.

Dependencies: [[US-125-restore-the-snapshot-into-test-databases|US-125]] is `Done`, because the road values come from the snapshot and no raster tiles are needed, and [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]] is `Done`.

## Status history

- **2026-10-12, draft.** Raised with [[decision-log|D-039]].

## Evidence and details

Fill this when the story reaches `Done`.
