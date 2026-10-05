---
date: 2026-10-05
type: plan
branch: front-end-according-to-mock-up
status: done
tags: [plan, sprint-7, airflow, edge-depth-table, us-041, postgis, raster]
related: ["[[edge-depth-table]]", "[[edge-depth-table-stories]]", "[[edge-depth-table-format]]", "[[sprint-plan-2]]", "[[flood-on-roads]]", "[[minio-flood-extent-pipeline]]", "[[graphhopper-backend]]", "[[routing-not-time-aware]]"]
---

# Plan: the Airflow task that writes each run's edge depth table (US-041)

## Context

Sprint 7 of [[sprint-plan-2]] has three rows. `US-041` (Story E3, P0, L) is the one the other two wait for. `US-042` publishes the table atomically and keeps the newest three. `US-044` documents the re-import procedure. This plan covers `US-041` only.

Acceptance, from [[edge-depth-table-stories]] Story E3. Given a real run and the export from `US-039`, when the task runs after `9b_load_depth_raster`, then it samples the raster tiles along each edge, stores the deepest 1 m sample in centimetres, tags the file with the graph hash, and reports its duration and size. For 20 hand-picked edges the values equal a direct `ST_Value` reading. An edge outside the model reads 0.

The build-time limit (user, 2026-10-02): the task runs beside the tile task, never delays it, and ends within 5 minutes of the end of `3_calculate_depth`.

## What is already there

1. The file format and its Python writer, `scripts/edge_depth/edge_depth_table.py` (`TableHeader`, `write_table`, 25 tests).
2. The export, `ExportEdges` in `java/time-aware-routing/`. It gives `edges.csv` (`edge_id,wkt`) and `graph.json` (`graph_hash`, `edge_count`). On the server graph: 67,833 edges, 51,328 nodes.
3. The sampling method, in `scripts/flood_roads/flood_on_roads.py`. It samples the midpoint of every metre along a line, matches each sample to its pixel by grid arithmetic and an equality join on the wet pixels, and takes the maximum. It reads one step for 15,285 pieces in 1.9 s on a local database. Calling `ST_Value` per sample was 12 times slower ([[flood-on-roads]]).
4. `flood_depth_raster_tile`, filled by `9b_load_depth_raster`, in EPSG:4326 with 256 by 256 pixel tiles, the newest 8 runs.
5. A throwaway PostGIS for tests. `postgresql-16-postgis-3` is installed in the cloud session, and `FLOOD_ROADS_TEST_DSN` style tests run against it (the 9 `flood_on_roads` tests pass).

## Design

The export lives outside Airflow. `ExportEdges` runs in the GraphHopper image, which Airflow cannot start. So the export is a pair of files in a folder that Airflow reads, and `US-044` documents how an operator regenerates them after a graph re-import.

1. **Two tables hold the export in PostGIS.** `graph_edge (edge_id, geom, length_m)` with a GiST index, and a one-row `graph_edge_export (graph_hash, edge_count, loaded_at)` that records which export `graph_edge` holds. Created by `0b_ensure_schema`.
2. **Load only when the hash changes.** The task reads `graph.json`. If the stored hash equals it, the load is skipped. If not, one transaction replaces every row. A re-import therefore needs no manual database step, and a table is never built from edges of another graph.
3. **Sample like `flood_on_roads`.** The same SQL with `graph_edge` in place of `road_segment`. The statistic matches decision D-006 and the PRD. Only edges that touch a tile with a wet pixel are sampled, so every other edge reads 0, which also gives "outside the model reads 0".
4. **Convert to centimetres.** `round(depth_m * 100)`, capped at 65,535 (the format holds `uint16`).
5. **Write the file.** `<EDGE_TABLE_DIR>/<run_ts>.bin`, through a temporary name and one rename, with the header from [[edge-depth-table-format]]: the graph hash, the run name, the step times (UTC), and the edge count. `US-042` adds the `latest` pointer, retention, and the storage choice. `US-041` does not.
6. **The task must not fail the DAG run.** `hotstart_policy` lets a run hotstart only if the previous slot's run is `success` or `running`, so a failed table task would force cold starts. A DAG run takes its state from its leaf tasks. The table task therefore gets one downstream no-op task with `trigger_rule="all_done"` that becomes the leaf. A failure stays red in the graph, the run stays green. The default `retries=1` still applies.
7. **Report.** The task prints and pushes to XCom the run, step count, edge count, wet edges per step, the sampling seconds, the file size, and the seconds in total.

Paths: `EDGE_EXPORT_DIR` defaults to `<DATA_PATH>/graph_export`, and `EDGE_TABLE_DIR` to `<DATA_PATH>/edge_depth`. Both are under the data folder that the Airflow containers already mount, so `compose.yml` does not change.

## Steps

Tests first at every step, and each step ends in a state I can run.

1. `scripts/edge_depth/graph_edges.py`: read and check an export, load it into `graph_edge` only when the hash differs. Tests against PostGIS.
2. `scripts/database/create_graph_edge_table.py`, wired into `task_ensure_schema`.
3. `scripts/edge_depth/build_edge_depth.py`: sample a run, convert, write the file, return the report. Tests on synthetic tiles, where each edge runs along a pixel row so the expected depths are exact (the posture of `test_flood_on_roads.py`).
4. `scripts/edge_depth/spot_check.py`: picks N wet edges and compares the table with a direct `ST_Value` reading at the same sample points. This is the acceptance check, and it runs on the server.
5. The DAG: `9c_build_edge_depth_table` after `9b_load_depth_raster`, plus the no-op leaf. Update `test_flood_mapping_dag_graph.py`.
6. Docs: [[edge-depth-table-format]], a new concept page for the build, `TODOS.md` and the sprint plan.

## Not in this story

- The `latest` pointer, retention, atomic publish across readers, and the storage choice (`US-042`).
- The stale-table check and the re-import page (`US-044`).
- The Java reader (`US-043`) and the proof on the server (`US-045`).

## Risks

- **Build time on the server is unmeasured.** The local figure is 1.9 s per step for pieces. `US-045` measures the real task against the 5-minute limit, and this story reports the duration on every run.
- **Edge geometry is not the road piece geometry.** An edge between junctions can be long. A 1 m sample spacing handles it, but the first server run is where a surprise would show.
- **The export folder is empty on a fresh server.** The task then fails with a message that names the folder and `export-edges.sh`, and the run stays green (design point 6).

## Status history

- **2026-10-05, active.** Plan written at the start of Sprint 7. Design points 1 to 7 and the step order are fixed. A throwaway PostGIS is available in the cloud session for the tests.
- **2026-10-05, active.** Steps 1 to 6 built and tested: `graph_edges.py`, `create_graph_edge_table.py`, `build_edge_depth.py`, `spot_check.py`, the DAG task and its `all_done` leaf, and the docs. 59 tests in `scripts/edge_depth/`, and a mutation check showed the sampling test catches a shallowest-instead-of-deepest change. Added `server_check.sh` and `EXPORT_DEST` in `export-edges.sh` for the server run. Waiting for that run: the 20-edge spot check, and the duration against the 5-minute limit.
- **2026-10-05, done.** Ran on the server through the Airflow worker (the DAG is paused): export written to `D:/airflow_new_data/data/mapping/graph_export`, table built for run `20261005T120000` in 42.0 s, 160 of 160 spot-check values equal. `US-041` is `Done`. The first run through a real DAG run is still to see, and `US-045` measures the 5-minute limit under load.
