---
date_drafted: 2026-10-10
type: user-story
us_id: "US-111"
title: "Show a pinned demo flood when no rain is forecast"
epic: "[[EP-17-flood-data-pipeline-and-core-output|EP-17]]"
status: Not started
kind: story
priority: P2
estimate: L
sprint: 
subsystem: flood-extent
source_ideas: []
related: ["[[decision-log|D-030]]", "[[decision-log|D-013]]", "[[minio-flood-extent-pipeline]]", "[[core-output-contract]]", "[[edge-depth-table-format]]", "[[US-088-cut-the-hanoi-storm-of-2026-09|US-088]]", "[[US-102-replay-the-storm-with-the-us-101-fix-to|US-102]]"]
tags: [user-story]
---

# US-111 Show a pinned demo flood when no rain is forecast

As a visitor who opens the flood map on a day with no forecast rain, I want the map, the routing, and the depth popup to use a pinned demo flood with a warning, so the map has a flood to show when the simulation has none.

The flood map has three modes, set by the rain forecast from Tomorrow.io ([[decision-log|D-013]]) and the steps the simulation has published ([[decision-log|D-030]]).

- **LIVE:** rain is forecast above the threshold, or a standing flood exists, and real simulation steps are published. The map shows the real result, as today.
- **PENDING:** rain is forecast, but the simulation has published no step yet. The map shows a dry map with a warning that the simulation is running.
- **DEMO:** no rain is forecast past the threshold and no flood stands. The map shows the demo flood with the warning "No flood forecasted, displaying the demo flood of Sep 16, 2026", in English only.

The demo is one static frame, the peak step of the 12-hour replay of the 2026-09-16 storm ([[US-088-cut-the-hanoi-storm-of-2026-09|US-088]]).
It has no slider and no animation.

Given no rain is forecast past the threshold and no flood stands, when a visitor opens the flood map, then the map shows the pinned demo flood and the warning "No flood forecasted, displaying the demo flood of Sep 16, 2026".

Dependencies: [[US-102-replay-the-storm-with-the-us-101-fix-to|US-102]] ran the replay that supplies the peak step.
The DAG was not changed while that replay ran.

## Split before Ready

This story is an L.
An L is split before it is Ready, as [[scrum-framework]] requires.
The plan below suggests four parts, one story each, and each part takes its own story ID when it is split out.

## Plan

1. **A DAG status row.**
   Task `0_check_forecast_rain` writes a status row with the rain gate decision for the run.
   The backend reads that row to pick LIVE, PENDING, or DEMO.
   The signal is a proposal, and the story that builds it confirms or changes it.
2. **Pinned demo data.**
   In DEMO mode the tiles, the routing, and the depth popup all use the pinned demo flood, not the tiles alone.
   Choose the peak step from the runs the replay makes.
   The tile build tiles only the first `FLOOD_EXTENT_TILE_STEPS` (2) steps of each run, so copy the peak step's tiles before the prune removes them.
   A 15-minute cycle prunes a run after about 2 hours, at 8 runs in `FLOOD_EXTENT_KEEP_RUNS`.
   The peak step must also survive these prunes: `flood_extent_step`, `flood_extent_polygon`, `flood_depth_raster_tile`, `flood_road_values` (`prune_flood_road_values`), and the routing edge tables (`EDGE_TABLE_KEEP_RUNS`, 3 runs).
3. **A backend mode endpoint.**
   The endpoint returns LIVE, PENDING, or DEMO from the status row.
   Open point: how the router reads a pinned step after the edge tables are pruned.
4. **The frontend banner and the pinned step.**
   The map shows the warning text in English only, and the DEMO frame with no slider.
   In PENDING mode the map shows a dry map with the simulation warning.
5. **Update the concept pages.**
   Update [[minio-flood-extent-pipeline]] and [[core-output-contract]] for the status row and the pinned step, and bump `last_updated`.

## Acceptance check

On the server, after the change is pulled and the replay has stopped.
Use a test point inside the model border (`.claude/CLAUDE.md`).
Take a screenshot of each mode for the evidence section.

1. Given no rain is forecast past the threshold and no flood stands, when the flood map loads, then the pinned demo flood shows with the exact warning text.
2. Given rain is forecast above the threshold and no step is published, when the flood map loads, then the map is dry and the warning says the simulation is running.
3. Given rain is forecast and real steps are published, when the flood map loads, then the map shows the real result as today.
4. Given DEMO mode, when a visitor taps a point inside the flooded area, then the depth popup reads the pinned step, and a route request is judged on the pinned flood.
5. Given the replay has made more runs than `FLOOD_EXTENT_KEEP_RUNS` and `EDGE_TABLE_KEEP_RUNS` allow, when the prunes have run, then the pinned step still has its tiles, its rows, and its edge table.

## Status history

- **2026-10-10, draft.**
  Written from decision [[decision-log|D-030]].
  No code is written, and no branch holds the feature.

## Evidence and details

Fill this when the story reaches `Done`.
