---
date_drafted: 2026-09-24
type: user-story
us_id: "US-030"
story_label: "4"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Done
priority: P0
estimate: M
sprint: 2
subsystem: airflow-pipeline
related: ["[[EP-06-raster-first-pipeline]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Switch routing to the new task and retire the GeoJSON tasks"
---

# US-030 Switch routing to the new task and retire the GeoJSON tasks

As a maintainer, I want tasks 4 to 8 gone and routing reading the new table, so the DAG has one path from depth rasters to routing data.
Given the shadow comparison passes, when the DAG is rewritten, then tasks 4 to 8 no longer exist, `run_ts` comes from `flood_extent.stamp_key`, a full cycle succeeds on the server, and a graded
`POST /route` returns a route built from the new table.
Dependencies: Story 3.
Evidence: ![[raster-first-pipeline-sprint2-verification.png|420]]
Details:
1. What: the DAG no longer builds GeoJSON.
   It loads roads and computes flood on roads into `flood_road_values`, the table routing reads.
2. How: `stage-b` removes tasks 4 to 8, `dags/test_dag.py`, and the `flood-results-full` configuration, and adds the `load_road_segments` and `flood_on_roads` tasks.
   On the server the bucket (15 objects, 14.7 MB) and the old `flood_depth_raster` table (122 MB) were deleted, and `flood_on_roads` was written in place for run `20260924T164803`.
3. Why: one path from the depth rasters to routing, with the raster as the source of truth.
4. Effect: routing now reads the new rows.
   Graded routes detour around flooded pieces (for example 111 m becomes 6,262 m around a 2.76 m piece), and two test routes have no connection once the flood applies.
   The old scripts (`extract_geojson_full.py`, `mapping_geojson.py`, `merge_geojson.py`, `upload_minio.py`, and their two callers) are deleted (2026-09-29).
   A full cycle succeeded on the server 2026-09-29 (`scheduled__2026-09-29T09:15:00+00:00`, all 10 tasks green).
   Graded `POST /route` confirmed live on real current data: the same two points connect (1256.4 m) ungraded and lose connection ("Connection between locations not found") once the live `flood_road_values` custom_model applies.
   Still open: the frontend on a live event (the state-test DAG will provide one, see D-007), and dropping the `flood_road_values_shadow` table on the server (an operational step, not code; `flood_on_roads.py`'s `create_shadow_table` and `compare_with_old.py` stay, they're live comparison tooling).
