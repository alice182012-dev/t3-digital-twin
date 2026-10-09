---
date_drafted: 2026-09-29
type: user-story
us_id: "US-041"
story_label: "E3"
epic: "[[EP-18-time-aware-routing-engine]]"
status: Done
priority: P0
estimate: L
sprint: 7
subsystem: airflow-pipeline, floodmap-backend
related: ["[[EP-08-edge-depth-table]]", "[[SP-02-routing-engine-foundations|sprint-plan-2]]"]
title: "Build the Airflow task that writes each run's table"
---

# US-041 Build the Airflow task that writes each run's table

As the routing engine, I want one depth value per edge and step for each run, so it can look up depth by
edge id.
Given a real run and the export from Story E1, when the task runs after `9b_load_depth_raster`, then it
samples the raster tiles along each edge, stores the deepest 1 m sample in centimetres, tags the file with
the graph hash, and reports its duration and size. For 20 hand-picked edges the values equal a direct
`ST_Value` reading. An edge outside the model reads 0.
Dependencies: Stories E1, E2 (both done).
Evidence: ![[us-041-edge-depth-table-server-output.png|700]]
Details:
1. What: task `9c_build_edge_depth_table` of `flood_mapping_full`, and the code in `scripts/edge_depth/`. For each run it writes `<run>.bin`: the deepest 1 m flood sample along every GraphHopper edge, in centimetres, at every step, in the `US-040` format, tagged with the graph hash of the export. It also has an export loader (`graph_edges.py`), a spot check (`spot_check.py`), and two server scripts.
2. How: tests first against a throwaway PostGIS (59 tests in `scripts/edge_depth/`, 16 in the DAG graph test). The sampling is the SQL of `flood_on_roads` with `graph_edge` in place of `road_segment`. The export is loaded into PostGIS only when its hash changes, in one transaction. The file is written under a temporary name and renamed. The task is followed by a no-op `all_done` task, so a failed table task does not fail the DAG run and the next slot can still hotstart. On the server the table was built inside the Airflow worker with `server_check.sh`, and the spot check read the same sample points with `ST_Value`.
3. Why: the routing engine and the departure timeline both need depth by edge id, and no table of that shape existed. The 20-edge spot check is the acceptance check of the story.
4. Effect: on 2026-10-05 on the server, for the retained run `20261005T120000`, the table has 67,833 edges and 8 steps, 1,085,487 bytes, graph hash `8c13d884...`. Each step took about 5 s to sample, and the whole build took 42.0 s. About 1,000 edges are wet at each step. All 160 values (20 edges at 8 steps, 10 wet and 10 dry) equal a direct `ST_Value` reading. `US-042` and `US-044` can start, and `US-045` can measure the task under pipeline load.
5. Limits: the table was built by running `build_edge_depth.py` in the Airflow worker, the same code the task runs, and not through a DAG run, because the DAG is paused. The wiring in a real Airflow run is not seen yet. The 42.0 s was measured with no other load, and the 5-minute limit counts from the end of `3_calculate_depth` in a live run, which `US-045` measures. The deepest checked value is 130 cm. The task fails, red and without failing the run, until an export is in `EDGE_EXPORT_DIR`, so an operator writes it first (`export-edges.sh` with `EXPORT_DEST`). The evidence image is rendered from output the user pasted.
