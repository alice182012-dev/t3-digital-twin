---
date_drafted: 2026-10-12
type: user-story
us_id: "US-118"
title: "Write the edge depth to a queryable table"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: Not started
kind: story
priority: P1
estimate: M
sprint: 
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

## Evidence and details

Fill this when the story reaches `Done`.
