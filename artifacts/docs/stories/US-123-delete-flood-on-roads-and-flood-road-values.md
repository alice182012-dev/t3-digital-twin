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
- **2026-10-13, In progress.** The code change is committed on `modular` and not on the server. A subagent wrote it and the main session reviewed the diff. 36 files changed, with about 2,500 lines deleted. `scripts/flood_roads/`, `scripts/roads/`, `create_flood_road_tables.py`, `create_road_segment_table.py`, and `geojson_to_pg.py` are deleted. The DAG `routing_adapter` keeps only `9c_build_edge_depth_table`, which emits the asset `edge_depth` (`EDGE_DEPTH_ROWS`) after its rows and its registry row are committed, and `flood_history` runs on that asset. A search of `dags`, `scripts`, `floodmap`, `test`, `analysis-service`, `java`, `minio_custom`, `compose.yml`, `README.md`, and `Dockerfile` for the retired names finds nothing, and every DAG file parses. The tests of `test/` give the same 10 failures and 2 collection errors as a clean `modular` (the failures are in the rain gate and 3Di alert tests), and 117 pass, 7 fewer than before because their tests were deleted. The test dataset scripts changed: `restore_snapshot.py` does not load the old tables, and `build_history_and_metrics.py` takes its runs from `edge_depth_run`. The contract page and the concept pages are updated, and the pages of the sampler and the road table moved to `archive/concepts/`. Still open: the pull on the server after the 50-run check ends, a run of `routing_adapter` with no `flood_on_roads` task and under 5 minutes from `3_calculate_depth` to the end of `9c`, the check of the three endpoints, the rebuild of `analysis` (its list of outputs lost `road_values`), the rerun of `create_routing_reader_role.py`, and the drop of the tables, which needs the owner's confirmation.

## Evidence and details

Fill this when the story reaches `Done`.

Note of 2026-10-13: the table `flood_road_values_shadow` (8,444 rows, 8.8 MB, written by the shadow run of `flood_on_roads --target`) also has no reader and joins the tables to drop ([[US-110-decide-whether-pipeline-tables-leave-the-public-schema|US-110]], details item 5).
