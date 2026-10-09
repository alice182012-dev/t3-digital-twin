---
date_drafted: 2026-10-08
type: user-story
us_id: "US-095"
story_label: "2"
epic: "[[EP-15-archive-and-netcdf-retirement]]"
status: Not started
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
a go, and two readings. Priority: P1. Status: Not started. Sprint: 11 (the user's choice). Dependencies: `US-094`.
Evidence: None yet.
