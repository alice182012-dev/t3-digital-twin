---
date_drafted: 2026-10-12
type: user-story
us_id: "US-121"
title: "Read the flood metrics from the edge table"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: Ready
kind: story
priority: P2
estimate: M
sprint: 14
subsystem: routing, flood-data, core-output
source_ideas: []
related: ["[[decision-log|D-038]]", "[[US-115-decide-whether-the-edge-depth-table-replaces-flood-road-values|US-115]]"]
tags: [user-story]
---

# US-121 Read the flood metrics from the edge table

As an analyst, I want the flood metrics of each road to be built from the edge table, so they stay valid after a graph re-import.

`extract_run.py` loads each piece's series from `flood_road_values` by `segment_id` and road name, and writes `flood_segment_metrics`.
The story re-keys the metrics on `edge_key` and decides how a road with several edges is reported, because the metrics count pieces today and the engine counts edges.
It keeps the thresholds of `impassable_from_m` and the rule that a dry run gives 0 cm ([[decision-log|D-036]]).

Given a replay run, when `extract_run.py` runs on the new table, then every edge with a wet step has metric rows, and the story records how the totals differ from the piece-based totals.
Given a run with no wet edge, then the script writes no metric rows and exits without error, where it raises today.
Given a graph re-import, then the metrics of the old keys are kept and marked, by the rule of [[US-117-export-a-stable-key-with-each-graph-edge|US-117]].

Dependencies: [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]] is `Done`.

## Status history

- **2026-10-12, draft.** Split from [[decision-log|D-038]], which replaces `flood_road_values` with the edge depth table in stages. It stays in the backlog until the owner accepts the decision.
- **2026-10-12, Ready.** Picked for [[SPR-014-finish-the-remaining-backend|SPR-014]] at the product owner's request, and `Ready` after the INVEST check: its dependencies are `Done` or in the same sprint, and its acceptance check is written.

## Evidence and details

Fill this when the story reaches `Done`.
