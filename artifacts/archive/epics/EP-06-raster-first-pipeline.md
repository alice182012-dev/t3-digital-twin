---
date_drafted: 2026-09-24
type: user-story
us_ids: ["US-027", "US-028", "US-029", "US-030", "US-031"]
status: draft
subsystem: airflow-pipeline
source_ideas: []
related: ["[[SP-01-prd-and-backlog|sprint-plan]]", "[[raster-first-flood-pipeline]]", "[[EP-03-point-depth-lookup-backend|point-depth-lookup-backend]]", "[[EP-04-timescaledb-and-flood-metrics|timescaledb-and-flood-metrics]]", "[[US-017-route-forecast-query|route-forecast-query]]", "[[BL-003-airflow-cannot-import-flood-utils|airflow-cannot-import-flood-utils]]"]
tags: [user-story, epic, airflow, postgis, raster, sprint-2]
---

# Epic: raster-first flood pipeline

Replaces the GeoJSON chain (tasks `4_extract_geojson_full` to `8_upload_postgres`) in
`dags/flood_mapping_dag.py` with tasks that read the depth rasters directly. The design and the
order of work are in the plan [[raster-first-flood-pipeline]]. Rows carry Priority, Status,
Estimate, and Sprint per the vault's sprint-delegation convention.

- [[US-027-load-the-roads-into-postgis-with-a|US-027]] Load the roads into PostGIS with a stable segment ID. Story 1.
- [[US-028-store-depth-rasters-as-tiles-and-read|US-028]] Store depth rasters as tiles and read them through a spatial index. Story 2.
- [[US-029-compute-flood-on-roads-from-the-raster|US-029]] Compute flood on roads from the raster into a shadow table. Story 3.
- [[US-030-switch-routing-to-the-new-task-and|US-030]] Switch routing to the new task and retire the GeoJSON tasks. Story 4.
- [[US-031-create-the-netcdf-table-in-the-schema|US-031]] Create the netcdf table in the schema task. Story 5.

## Status history

Story-level progress lines up to 2026-10-10 are in [[EP-06-raster-first-pipeline-history|the archived history]]. This section keeps plan-level changes only.

- **2026-09-24, draft.** Drafted from the plan [[raster-first-flood-pipeline]] after the user chose to
  retire the GeoJSON tasks. All five stories go in Sprint 2, since [[US-017-route-forecast-query|route-forecast-query]] and
  [[EP-04-timescaledb-and-flood-metrics|timescaledb-and-flood-metrics]]'s Story 4 need the segment ID and the new roads table.
- **2026-09-25, draft.** Story 4 is `In progress` on `stage-b`. Built: the DAG retirement, the road loader and
  `flood_on_roads` tasks (11 tasks, 15 edges, loaded in a real `DagBag` on the server), the removal of
  `dags/test_dag.py` and the `flood-results-full` configuration, and routing on `depth_max` (D-005). Not done:
  the server deploy, a full cycle, a graded `POST /route` on the new rows, and deleting the old scripts.
- **2026-09-25, draft.** Story 4 progress on the server: deleted the `flood-results-full` bucket and `flood_depth_raster`, wrote
  `flood_on_roads` in place for run `20260924T164803` (8,444 rows replacing 7,620), and confirmed graded routing on the new rows.
  Still `In progress`: a full cycle, the frontend on a live event, and deleting the old scripts.

