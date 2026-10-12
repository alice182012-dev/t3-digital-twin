---
date_drafted: 2026-10-12
type: user-story
us_id: "US-115"
title: "Decide whether the edge depth table replaces flood_road_values"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: Ready
kind: spike
priority: P0
estimate: M
sprint: 13
subsystem: routing, flood-data, core-output
source_ideas: []
related: ["[[edge-depth-table-format]]", "[[core-output-contract]]", "[[flood-on-roads]]", "[[decision-log|D-006]]", "[[decision-log|D-032]]", "[[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]]"]
tags: [user-story, spike]
---

# US-115 Decide whether the edge depth table replaces flood_road_values

As the owner of the flood data, I want to know whether one sampler and one table can replace both `flood_road_values` and the edge depth table, so the map, the route fallback, the rain gate, and the depth history all read the same water that the routing engine routes on.

**Why now.**
A run in which no road piece is wet writes no rows to `flood_road_values`.
The winner query of `flood_areas.py` then lets an older, wetter run win for those times, so the map overlay and the route fallback show water that has dried.
The time-aware engine does not have the problem, because its edge depth table is dense (0 for a dry edge).
The `depth_history` of [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]] reads `flood_road_values`, so the answer decides what that story builds.

**Question.**
Can the edge depth build (task `9c`) feed a queryable table that serves all four readers of `flood_road_values`, and what does the swap cost?

**Timebox.**
Half a sprint, on a copy of the server data in `marie-curie/`, with read-only checks on the server.

The spike answers these points, each with a measured result or the code that proves it:

1. Does a fully dry run reach the readers wrongly today?
   Read the failure path of `extract_run.py` when a run has no rows, and how the DAG that calls it reacts.
   Read how the Java engine picks the table for a time, so the claim "the engine is safe" is checked and not assumed.
2. Does `graph_edge` map to a stable key (`segment_id` or the OSM way) that survives a graph re-import?
   If it does not, say what history keyed on `edge_id` loses at each re-import.
3. What does a sparse table of wet edges per step cost?
   Count rows per run against the 19,656 of `flood_road_values`, and size 24 hours of runs.
4. What does one sampler change in the build time of `9c` against its 5-minute limit ([[BL-023-9c-sampling-step-runs-over-770-seconds|BL-023]])?
5. What does each reader need: the overlay and fallback (geometry and a depth band per forecast time), the rain gate (the maximum per run), the metrics (a per-piece series), and the soak checks?

Given the spike on a copy of the server data, when it ends, then the story holds the answers to the five points and a decision `D-nnn` that says replace now, replace later with a trigger, or keep both and fix the winner query with the run registry.
The decision names the stories it creates, and it says what changes for [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]].

Dependencies: None.

## Status history

- **2026-10-12, Ready.** Raised at Sprint 13 planning from the question "what does routing do with a run that wets no road piece". The product owner asked for it to be worked first in the sprint. Sized M (3 points) against `US-001`: several code reads, a data query, and a check on the server.

## Evidence and details

Fill this when the spike ends.
A spike records its measured result instead of a screenshot.
