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
- **2026-10-13, In progress.** Pre-flight on the server, with no write. The server checkout is clean on `modular` and 27 commits behind `alice/modular`, so `git pull --ff-only alice modular` is a plain fast-forward. The pull changes no `compose.yml`, `Dockerfile`, or `requirements.txt`, so no container is recreated. Only `analysis-service/app/server.py` changes in behaviour (its list of core outputs), so only `analysis` needs a rebuild. The backend changes are docstrings. The new `dags/` and `scripts/` import in the worker with Airflow's `DagBag` from a temporary folder with no import error: `routing_adapter` has only `9c_build_edge_depth_table`, `flood_history` has `load_depth_history`, and `flood_mapping_full` has 9 tasks. In `minio_custom`, no view, function, or trigger depends on the four tables, and one foreign key joins them (`flood_road_values` to `flood_road_file`), so the drop runs `flood_road_values` first. The grants that go with them are `routing_reader` (`flood_road_file`, `flood_road_values`) and `analysis_reader` (`flood_road_values`). `timescaledb` holds no copy. The four tables take 377 MB (358, 11, 8.8, and 0.2). The run of 03:45 UTC is frozen at `3b_publish_depth_files`, its depth folder `depth_20261013_110000_124500` exists, and the pool `routing_adapter` (1 slot) exists. `routing_adapter` and `flood_history` are unpaused. The owner approved the unpause of `flood_mapping_full` after the 50-run check.
- **2026-10-13, In progress.** The server steps ran, except the rebuild of `analysis` and the drop of the tables, which wait for the owner. The pull of `modular` was a fast-forward to `08cdbb3`, with no import error. `create_routing_reader_role.py` ran for both roles in the worker: `routing_reader` reads 9 tables, `analysis_reader` reads 4, and no grant is left on the four old tables. The owner's unpause of `flood_mapping_full` at 09:39:53 UTC resumed the run of 03:45 UTC. After `3_calculate_depth` (ended 03:49:17), `3b_publish_depth_files` took 1 s (09:39:34), `9b_load_depth_raster` took 119 s (until 09:41:33), `routing_adapter` ran only `9c_build_edge_depth_table`, which took 25.5 s (until 09:41:59.6), and `flood_history` loaded the run in 0.4 s from the new asset `edge_depth`. From the restart after the pause to the end of `9c` is 145 s, against the limit of 5 minutes, and the 8 steps of run `20261013T110000` are in `flood_depth_raster_tile` and `edge_depth_run`. The comparison of the endpoints, `marie-curie/us123/capture.sh` before and after, gives 16 identical answers of `/flood/points` and `/flood/areas` in each mode, and no difference in the path, the distance, or the geometry of the 16 routes. The differences are the timing `info.took`, the `decided_at` of the mode, and, in `LIVE`, the run that the engine judges (`20261013T104500` before, `20261013T110000` after, because a run was published). The resumed run counted as a fresh publish, so the standing-flood rule opened the gate of the slot of 09:45 UTC with a forecast of 0 mm/h, and real simulations continue until 5 dry runs in a row ([[US-139-skip-a-flood-run-whose-slot-is-hours-old|US-139]] closes this). Still open: the rebuild of `analysis` from the desktop, and the drop of `flood_road_values`, `flood_road_file`, `road_segment`, and `flood_road_values_shadow` after the owner confirms.

## Evidence and details

Fill this when the story reaches `Done`.

Note of 2026-10-13: the table `flood_road_values_shadow` (8,444 rows, 8.8 MB, written by the shadow run of `flood_on_roads --target`) also has no reader and joins the tables to drop ([[US-110-decide-whether-pipeline-tables-leave-the-public-schema|US-110]], details item 5).
