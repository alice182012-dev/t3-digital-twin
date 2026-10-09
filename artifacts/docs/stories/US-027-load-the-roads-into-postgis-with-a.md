---
date_drafted: 2026-09-24
type: user-story
us_id: "US-027"
story_label: "1"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Done
priority: P0
estimate: M
sprint: 2
subsystem: airflow-pipeline
related: ["[[EP-06-raster-first-pipeline]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Load the roads into PostGIS with a stable segment ID"
---

# US-027 Load the roads into PostGIS with a stable segment ID

As a pipeline engineer, I want the roads in a `road_segment` table keyed by a stable ID, so
routing data, TimescaleDB, and the route-forecast query all refer to the same road pieces.
Given `toa-do-duong-hanoi.geojson` (12,431 ways, each with a unique OSM id in `@id`), when the
loader runs twice, then `road_segment` holds the same `segment_id` values both times, every way
is present, and the pieces of each way add up to that way's length within 0.5 m.
Priority: P0. Status: Done. Estimate: M. Sprint: 2. Dependencies: None.
Evidence: ![[road-segment-server-check.png|420]]
Details:
1. What: a `road_segment` table with one row per road piece, keyed by `segment_id` such as `way/11835354#0`.
2. How: `load_road_segments.py` cuts each of the 12,431 ways into equal pieces of at most 50 m in EPSG:3405 and upserts them in one transaction.
3. Why: routing data, TimescaleDB, and the route-forecast query need one stable road ID, and the old mapping step dropped the OSM id.
4. Effect: it feeds the DAG tasks and the TimescaleDB key change. On the server (2026-09-25): 35,652 pieces, every way present, worst length error 0.000000000 m, and a second load changed nothing. IDs shift if the roads file or the piece length changes.
