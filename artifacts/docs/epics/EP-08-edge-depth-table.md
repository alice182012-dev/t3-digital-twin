---
date_drafted: 2026-09-29
type: user-story
us_ids: ["US-039", "US-040", "US-041", "US-042", "US-043", "US-044", "US-045", "US-070"]
status: draft
subsystem: airflow-pipeline, floodmap-backend
source_ideas: ["[[sticky-c-lite-routing]]"]
related: ["[[PRD-003-edge-depth-table|edge-depth-table]]", "[[SP-02-routing-engine-foundations|sprint-plan-2]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[EP-09-time-aware-routing-engine|time-aware-routing-engine-stories]]", "[[flood-on-roads]]"]
tags: [user-story, epic, airflow, graphhopper, raster, edge-id, sprint-5, sprint-6, sprint-7, sprint-8]
---

# Epic: edge depth table

The requirements are in [[PRD-003-edge-depth-table|edge-depth-table]]. The engine that reads the table is in
[[EP-09-time-aware-routing-engine|time-aware-routing-engine-stories]]. The order of work is in [[SP-02-routing-engine-foundations|sprint-plan-2]].

Each row carries Priority, Status, Estimate, Sprint, and Dependencies, as an extension of the base Epic
shape in [[user-story-types]]. Sprint numbers continue from [[SP-01-prd-and-backlog|sprint-plan]]. A story reaches `Done` only with
a screenshot and numbered details, recorded here and in `sprint-plan-2.md`.

- [[US-039-export-the-graph-s-edges|US-039]] Export the graph's edges. Story E1.
- [[US-040-define-the-table-format-and-write-the|US-040]] Define the table format and write the Python reader and writer. Story E2.
- [[US-041-build-the-airflow-task-that-writes-each|US-041]] Build the Airflow task that writes each run's table. Story E3.
- [[US-042-publish-the-table-atomically-and-keep-the|US-042]] Publish the table atomically and keep the newest three runs. Story E4.
- [[US-043-build-the-java-reader-with-a-hash|US-043]] Build the Java reader with a hash check and reload without restart. Story E5.
- [[US-044-document-the-graph-re-import-procedure-and|US-044]] Document the graph re-import procedure and detect a stale table. Story E6.
- [[US-045-prove-the-table-on-the-server|US-045]] Prove the table on the server. Story E7.
- [[US-070-stop-a-slow-sampling-step-from-holding|US-070]] Stop a slow sampling step from holding the database. Story E8.

## Status history

- **2026-09-29, draft.** Written from [[PRD-003-edge-depth-table|edge-depth-table]]. No story has started.
- **2026-10-01, draft.** Story E2 (`US-040`) is `Done`: the Python reader and writer pass 25 tests, and a table of 2,000,000 edges and 9 steps is 36.0 MB. Output rendered as `us-040-table-check-output.png`. The format is [[edge-depth-table-format]].
- **2026-10-02, draft.** The gate of Story E7 is cleared. The user accepted the build-time limit: the table task runs beside the tile task, never delays it, and ends within 5 minutes of the end of `3_calculate_depth` (see [[PRD-003-edge-depth-table|edge-depth-table]]).
- **2026-10-05, draft.** Story E1 (`US-039`) is `Reviewed`. `ExportEdges` in `java/time-aware-routing/` writes `edges.csv` and `graph.json` from a read-only graph cache. 18 tests pass in the module (9 new). On an Andorra import with the repo's four profiles and LM it wrote 2,820 rows for 2,820 edges, with identical output on two runs. Not done: the run on the server graph (expect 67,833 rows) and its screenshot. The hash algorithm is fixed now, see [[edge-depth-table-format]].
- **2026-10-05, draft.** Story E1 (`US-039`) is `Done`: on the live graph on the server (mounted read-only) the export wrote 67,833 rows for 67,833 edges, identical on two runs. Evidence: `us-039-edge-export-server-output.png`.
- **2026-10-05, draft.** Story E3 (`US-041`) is `Reviewed`. Task `9c_build_edge_depth_table` and its code in `scripts/edge_depth/` are built, tests first, against a throwaway PostGIS: 59 tests in `scripts/edge_depth/` and 16 in the DAG graph test. Sampling is the method of `flood_on_roads`, and a failed table task does not fail the run (a no-op `all_done` leaf). Not done: the run on the server graph, the spot check of 20 edges against `ST_Value`, and the duration against the 5-minute limit. Plan: [[edge-depth-table-airflow-task]]. Server steps: `export-edges.sh` with `EXPORT_DEST`, then `scripts/edge_depth/server_check.sh`.
- **2026-10-05, draft.** Story E3 (`US-041`) is `Done`. On the server, for run `20261005T120000`: 67,833 edges by 8 steps, built in 42.0 s, and all 160 values of the 20-edge spot check equal a direct `ST_Value` reading. Evidence: `us-041-edge-depth-table-server-output.png`.
- **2026-10-05, draft.** Story E4 (`US-042`) is `Reviewed`. `write_latest` now replaces the pointer in one step (a reader test reproduced the empty pointer on the old code first). `publish_edge_depth.py` checks the file, moves `latest` only forward under a folder lock, keeps the newest three, and removes stale temporary files. Task 9c publishes. `compose.yml` adds the volume `edge-depth-tables`. 83 tests in `scripts/edge_depth/` and 18 in the DAG graph test pass, and three mutations are caught. Not done: the volume on the server, and `publish_check.py` there (a polling reader in its own process). Storage chosen: a Docker named volume. Plan: [[edge-depth-table-publish]].
- **2026-10-05, draft.** Story E4 (`US-042`) is `Done`. On the server a reader in its own process made 11,878 reads while 41 tables published, none failed, and 3 tables were left. Evidence: `us-042-atomic-publish-server-output.png`.
- **2026-10-05, draft.** Story E6 (`US-044`) is `Reviewed`. Built: the page [[graph-reimport-procedure]], `StaleTableError`, `require_graph_hash` and `read_latest_table_for_graph` (Python guard, logs both hashes), and `scripts/edge_depth/check_tables.py` (compares the export folder, `graph_edge`, the `latest` table, the older tables, and the live graph's hash). 99 tests in `scripts/edge_depth/` pass. Not done: the run on the server (`server_check.sh` now shows a fresh and a stale case), and the Java refusal at request time, which is `US-043`. Plan: [[graph-reimport-procedure-and-stale-table-check]].
- **2026-10-05, draft.** Story E6 (`US-044`): the server check passed. With the export, `graph_edge`, and the `latest` table on hash `8c13d884...` the check says `FRESH`, and against another hash it says `STALE`, names both hashes, and exits 1. Evidence: `us-044-stale-table-check-server-output.png`. The status stays `Reviewed` until the user confirms the split with `US-043`.
- **2026-10-05, draft.** Story E6 (`US-044`) is `Done`. The user confirmed the split with `US-043`: the page, the Python guard, and the operator check are closed here, and the refusal at request time in the Java reader is `US-043`'s acceptance. Evidence: `us-044-stale-table-check-server-output.png`.
- **2026-10-05, draft.** Story E8 (`US-070`) is `Reviewed`. Built after task 9c ran over 770 s in one step during the replay. `ANALYZE` before sampling and a 120 s step limit, tests first (133 tests in `scripts/edge_depth/`, two mutations caught), pushed as `5e358bf`. Not done: the pull on the server and the next 9c log. It stays `Reviewed` until then.
- **2026-10-09, draft.** Story E7 (`US-045`) is `Done`. Over the 45 runs of the 12-hour replay, the gap from the end of `3_calculate_depth` to the end of 9c was 2.69 to 3.91 minutes, under the 5-minute limit. The table is 67,833 edges and 1,085,487 bytes, and `spot_check.py` passed (160 of 160) on `20261009T031500.bin`. The gap grows within a chain and resets at a restart, so `US-086` (the prune of `flood_road_values`) matters for a longer chain. Evidence: `us-045-table-timing-check-output.png`. Story E8 (`US-070`) stays `Reviewed`: 9c took 44.8 to 90.3 s, and no step passed the 120 s cancel, but the time does not level off near 50 s.
