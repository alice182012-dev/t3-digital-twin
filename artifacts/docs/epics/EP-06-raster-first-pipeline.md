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

- **2026-09-24, draft.** Drafted from the plan [[raster-first-flood-pipeline]] after the user chose to
  retire the GeoJSON tasks. All five stories go in Sprint 2, since [[US-017-route-forecast-query|route-forecast-query]] and
  [[EP-04-timescaledb-and-flood-metrics|timescaledb-and-flood-metrics]]'s Story 4 need the segment ID and the new roads table.
- **2026-09-24, draft.** Story 1 built and reviewed (`ff18140`, `fcc4a03`, `23fad9c`, merged). Status is
  `Reviewed`: it passed on a local PostGIS with the real roads file, and has not run on the server.
- **2026-09-24, draft.** Story 2 built and reviewed (`b239491`, `1238616`, `bc158e5`, `876cbe5`, merged).
  Status is `Reviewed`: the numbers come from a local PostGIS, and none is measured on the server.
- **2026-09-24, draft.** Story 2 deployed to the server (commit `6155f09`) and checked there: 4 timesteps of
  880 tiles, values equal to the earlier `gdallocationinfo` reference, tile lookup median 0.56 ms.
  Still `Reviewed`, because pruning needs a fourth run to show on the server.
- **2026-09-24, draft.** Decided: write `flood_road_values` in place, mean depth per piece with the maximum stored
  beside it, retire `dags/test_dag.py`, and remove the `flood-results-full` bucket. See [[raster-first-flood-pipeline]].
- **2026-09-24, draft.** Story 3 built and reviewed on `stage-b` (`55910af`, `b2387df`, `1ccddc9`, `89ac6a0`,
  `b2f04d4`). The old rows are not ground truth: every old depth equals the top-left pixel of a 20 m cell,
  because the server runs `SAMPLE_RATE=20`. Status is `Reviewed`: nothing ran on the server.
- **2026-09-25, draft.** Story 4 is `In progress` on `stage-b`. Built: the DAG retirement, the road loader and
  `flood_on_roads` tasks (11 tasks, 15 edges, loaded in a real `DagBag` on the server), the removal of
  `dags/test_dag.py` and the `flood-results-full` configuration, and routing on `depth_max` (D-005). Not done:
  the server deploy, a full cycle, a graded `POST /route` on the new rows, and deleting the old scripts.
- **2026-09-25, draft.** The user chose the maximum depth for every use (D-006). `depth` now holds the maximum and there is no
  `depth_max` column. A delegate is making the code and note changes on `stage-b`.
- **2026-09-25, draft.** Stage B checked on the server (`stage-b` at `2be63a4`). Story 1 and Story 3 are `Done`, each with
  a server screenshot. Story 5 is `Reviewed`: the netcdf tables now exist, and task 3b needs a real cycle. Story 4 stays
  `In progress`: writing in place, the bucket and old table removal, a full cycle, and a graded route remain.
- **2026-09-25, draft.** Story 4 progress on the server: deleted the `flood-results-full` bucket and `flood_depth_raster`, wrote
  `flood_on_roads` in place for run `20260924T164803` (8,444 rows replacing 7,620), and confirmed graded routing on the new rows.
  Still `In progress`: a full cycle, the frontend on a live event, and deleting the old scripts.
- **2026-09-29, draft.** Deleted the retired GeoJSON chain's source: `scripts/extract_geojson.py`,
  `scripts/mapping/extract_geojson_full.py`, `mapping_geojson.py`, `merge_geojson.py`, and
  `upload_minio.py`, plus their only two callers, `scripts/run_d1_ingest.py` and `test/test.py`
  (both local harnesses for the retired chain, confirmed unused by `dags/flood_mapping_dag.py` or
  anything else in the repo). `scripts/database/geojson_to_pg.py` stayed: `flood_on_roads.py` and
  `extract_run.py` still call it. Corrected a stale `test/test.py` reference in
  [[3di-simulation-orchestration]]. Still `In progress`: a full DAG cycle, the frontend on a live
  event, and dropping the `flood_road_values_shadow` table on the server (an operational step, not
  a code change; `flood_on_roads.py`'s `create_shadow_table` and `compare_with_old.py` stay, since
  they are live comparison tooling, not part of the retired chain).
- **2026-09-29, draft.** Stories 2, 4, and 5 are `Done`, all with server evidence from the same
  session: a real full cycle (`scheduled__2026-09-29T09:15:00+00:00`, all 10 tasks green, task 3b
  included), tile retention confirmed (8 runs kept, matching the current `FLOOD_RASTER_KEEP_RUNS`
  default of 8, raised from 3 by commit `002bdce`), and graded `POST /route` confirmed against live
  current data (a route that connects ungraded loses connection once the live `flood_road_values`
  custom_model applies). Still open on Story 4: the frontend on a live event, and dropping
  `flood_road_values_shadow` from the server (operational, not code).

