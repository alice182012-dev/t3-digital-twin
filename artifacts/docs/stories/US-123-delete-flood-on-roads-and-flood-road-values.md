---
date_drafted: 2026-10-12
type: user-story
us_id: "US-123"
title: "Delete flood_on_roads, road_segment, and flood_road_values"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: In progress
kind: story
priority: P2
estimate: S
sprint: 14
subsystem: routing, flood-data, core-output
source_ideas: []
related: ["[[decision-log|D-038]]", "[[US-115-decide-whether-the-edge-depth-table-replaces-flood-road-values|US-115]]"]
tags: [user-story]
---

# US-123 Delete flood_on_roads, road_segment, and flood_road_values

As the owner of the pipeline, I want the second sampler and its tables gone, so one procedure and one table hold the flood depth.

After the readers have moved, the task `flood_on_roads`, the task `load_road_segments`, the prune task, and the tables `road_segment`, `flood_road_values`, and `flood_road_file` have no reader.
The story deletes them and their scripts and tests, updates [[core-output-contract]] and [[flood-on-roads]], and records the freed time per run and the freed storage.

Given a search of the repository, when it looks for `flood_road_values`, `road_segment`, and `flood_on_roads`, then it finds only archived documents and this story.
Given a replay run on the server, when `routing_adapter` finishes, then it has no `flood_on_roads` task, and the time from `3_calculate_depth` to the end of `9c` is under 5 minutes.
Given the endpoints `/flood/areas`, `/route`, and `/flood/points`, then each answers as before the deletion.

Dependencies: [[US-119-read-the-map-overlay-and-route-fallback-from-the-edge-table|US-119]], [[US-120-read-the-rain-gate-and-soak-checks-from-the-edge-table|US-120]], [[US-121-read-the-flood-metrics-from-the-edge-table|US-121]], and [[US-122-point-depth-history-at-the-edge-table|US-122]] are `Done`.

## Status history

- **2026-10-12, draft.** Split from [[decision-log|D-038]], which replaces `flood_road_values` with the edge depth table in stages. It stays in the backlog until the owner accepts the decision.
- **2026-10-12, Ready.** Picked for [[SPR-014-finish-the-remaining-backend|SPR-014]] at the product owner's request, and `Ready` after the INVEST check: its dependencies are `Done` or in the same sprint, and its acceptance check is written.
- **2026-10-13, In progress.** The code change is written in a worktree by a subagent and will be checked before it reaches the server. The plan is in the next action of `TODOS.md`. The change keeps the test dataset scripts working: `restore_snapshot.py` stops loading the old road tables, and `build_history_and_metrics.py` takes its run list from `edge_depth_run`. The server needs the DAG unpaused for the replay run, and the tables are dropped only after the owner confirms.

## Evidence and details

Fill this when the story reaches `Done`.
