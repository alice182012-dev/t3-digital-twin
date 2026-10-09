---
date_drafted: 2026-10-08
type: user-story
us_id: "US-095"
story_label: "2"
epic: "[[EP-15-archive-and-netcdf-retirement]]"
status: In progress
priority: P1
estimate: M
sprint: 11
subsystem: core-output
related: ["[[EP-15-archive-and-netcdf-retirement]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
title: "Retire the `netcdf_values` ingest"
---

# US-095 Retire the `netcdf_values` ingest

As the operator of the server, I want the unused NetCDF-to-TimescaleDB ingest removed, so the DAG drops a task that
takes about 81 s per run and the `timescaledb` database stops growing by gigabytes.
Retire means removing task `3b_upload_netcdf_postgres`, the three TimescaleDB tables `netcdf_values`,
`mesh_elements`, and `netcdf_variable_catalog`, the two `storage-postgres` tables `netcdf_files` and `netcdf_variables`, and the scripts and tests that use them.
Verified on 2026-10-08. Database: the only foreign key is `netcdf_values.variable_id` to
`netcdf_variable_catalog(id)`, so drop `netcdf_values` first, then the catalog. `mesh_elements` has no foreign
keys. No views or continuous aggregates exist. The same database holds three other tables that are empty by design
(`institution_histogram_bar`, `background_forecast_depth`, `depth_history`), created by
`create_timescale_tables.py`. They must survive.
Code to change: `dags/flood_mapping_dag.py` (task `3b_upload_netcdf_postgres`, and `task_ensure_schema` at lines
175 to 176, which calls `create_netcdf_tables.create_tables()` and `create_timescale_tables.main()`, plus the
imports at lines 28 to 36); `scripts/database/` (`netcdf_to_pg.py`, `netcdf_variables.py`,
`backfill_netcdf_values.py`, `create_netcdf_tables.py`, and the `netcdf_values`, `mesh_elements`, and catalog parts
of `create_timescale_tables.py`); `test/test_flood_mapping_dag_graph.py` (asserts `3b` is a leaf and that
`0b_ensure_schema` calls `create_netcdf_tables`); `dags/flood_forecast_state_test_dag.py` and
`test/test_flood_state_test_dag_graph.py` (two references; this test DAG is unpaused on the server);
`scripts/storage_check/read_storage.ps1` (reads the `netcdf_values` size for `US-066` and `US-069`). Docs that
mention the ingest: `README.md` lines 83 to 84, the architecture doc, concept pages, and the `US-066` story and its plan.
`create_netcdf_tables.py` also creates `netcdf_files` and `netcdf_variables` on `storage-postgres`. The user decided
on 2026-10-08 that those two are dropped too. Their size and any dependents on `storage-postgres` are unverified, so
the story reads both before the drop. `netcdf_input` is a different module that feeds
`3_calculate_depth`. It stays.
Given the story is built, then the DAG graph has no `3b` task, its tests pass, and `0b_ensure_schema` still creates
the three empty tables. Given the user's explicit go on the server drop (the `US-066` precedent), then the three
tables are dropped in order, and the `timescaledb` size and the C: free space are recorded before and after. The
storage-check script no longer reads `netcdf_values`. Server facts: `netcdf_values` is 2,428 MB with a 48-hour
retention policy and 6-hour compression.
Do this only after `US-094` is proven on real rain, so no data is lost.
Estimate: M. About ten files change in one DAG, two test files and a script, and the server drop needs a deploy,
a go, and two readings. Priority: P1. Status: In progress. Sprint: 11 (the user's choice). Dependencies: `US-094`.
Evidence: None yet.

## Status history

- **2026-10-09, in progress.** The code removal is committed on the local branch `us-095-retire-netcdf-ingest` (`9b79b0d`, not pushed, not deployed). Removed: task `3b_upload_netcdf_postgres`, `netcdf_to_pg.py`, `netcdf_variables.py`, `backfill_netcdf_values.py`, `create_netcdf_tables.py`, the `netcdf_*` and `mesh_elements` parts of `create_timescale_tables.py`, and the `netcdf_values` reading of `read_storage.ps1` (the `flood_metrics` total size stays). The DAG graph tests expect no `3b` task and the leaves `9_build_flood_tiles` and `9b_load_depth_raster`. Not done: the doc updates (concept pages, architecture doc, `US-066`), which follow the deploy, and the server drop. Finding: `create_netcdf_tables.py` also created a third table, `netcdf_values`, on `storage-postgres` (foreign key to `netcdf_files`, `ON DELETE CASCADE`). Read it before the drop and decide whether it goes with the other two.
- **2026-10-09, server read (22:10 +07, read-only, `--context remote-server`).** The three `storage-postgres` tables are small: `netcdf_files` 752 kB and 316 rows, `netcdf_variables` 3,712 kB and 9,361 rows, `netcdf_values` 56 kB and 0 rows, so the drop frees about 4.5 MB. Two foreign keys point at `netcdf_files` (from `netcdf_variables` and `netcdf_values`, both `ON DELETE CASCADE`). The database has no view and no function that mentions `netcdf`, and no query touched the tables. Drop in this order: `netcdf_values`, `netcdf_variables`, `netcdf_files`, without `CASCADE`. Deploy the branch before the drop. The running DAG code still has task `3b` and `0b_ensure_schema` still calls `create_netcdf_tables`, so a dropped table comes back empty on the next run, and `3b` against a missing table fails with `relation "netcdf_files" does not exist` (the failure [[US-031-create-the-netcdf-table-in-the-schema|US-031]] fixed). Do not drop before the second replay ends at 00:45 +07 on 2026-10-10. The decision on the third table (`netcdf_values` on `storage-postgres`) is open: it holds 0 rows, so dropping it first costs nothing.
- **2026-10-10, checked against `US-101`.** `git merge-tree` of `modular` (with `5f115f4`) and the branch `us-095-retire-netcdf-ingest` has no conflict, and the merged DAG tests pass (the 6 old failures in `test/test_flood_rain_gate.py` are unchanged). The `US-101` rule does not read the `netcdf_*` tables. One dependency: while task `3b` still runs, a longer storm ingests more rows, about 13 MB per run (573 MB over 45 runs in the old TimescaleDB), until this story is deployed.
