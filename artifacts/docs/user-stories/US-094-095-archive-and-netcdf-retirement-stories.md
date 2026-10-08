---
date_drafted: 2026-10-08
type: user-story
us_ids: ["US-094", "US-095"]
status: draft
subsystem: core-output
source_ideas: []
related: ["[[sprint-plan-3]]", "[[decision-log]]", "[[core-output-hygiene-stories]]", "[[netcdf-values-storage-redesign]]", "[[3di-simulation-orchestration]]", "[[archive-3di-results-and-retire-netcdf-values]]", "[[move-non-ssd-storage-to-d-drive]]", "[[2026-10-08]]"]
tags: [user-story, epic, archive, netcdf, retention, sprint-10, sprint-11]
---

# Epic: archive the 3Di results and retire the netcdf_values ingest

Two decisions of 2026-10-08 (D-016 and D-018 in [[decision-log]]) become two stories. The first keeps each real-rain
run's `results_3di.nc` on the server's D: drive. The second removes the `netcdf_values` ingest, which holds 2,428 MB
on the server and costs about 81 s per run. Story 2 reads the archive that Story 1 proves, so Story 1 comes first.
Each row carries Priority, Status, Estimate, Sprint, and Dependencies, as an extension of the base Epic shape in
[[user-story-types]]. A story reaches `Done` only with evidence and numbered details, recorded here and in
[[sprint-plan-3]]. The plan is [[archive-3di-results-and-retire-netcdf-values]].

Concept pages and the architecture doc are not edited now. They change when the stories are built: [[3di-simulation-orchestration]],
[[architecture-block-diagram]], [[timescaledb-and-flood-metrics]] if it describes the ingest, and the US-066 pages.

- **Story 1 (US-094): Archive `results_3di.nc` and a run record to D: when the pipeline reads real rain.**
  As the owner of the case-study data, I want each real-rain simulating run's result file kept on D:, so a past storm
  can be analyzed after the 24-hour cleanup deletes `RESULT_DIR`.
  Given the DAG as it is, the cleanup runs inside `9_build_flood_tiles`: `publish.publish_run` receives
  `cleanup_dirs=[RESULT_DIR, DEPTH_ROOT_DIR, FLOOD_EXTENT_WORK_DIR]` (`dags/flood_mapping_dag.py` line 251) and the
  age limit `FLOOD_EXTENT_CLEANUP_MAX_AGE_HOURS` (24). Task `2_download_results` writes
  `RESULT_DIR/<sim_id>/results_3di.nc`. The new task copies that file after `2_download_results`, and
  `9_build_flood_tiles` waits for it, so the copy cannot race the cleanup. The task runs in parallel with
  `3_calculate_depth` and is not on the critical path.
  Given real-rain mode, when a simulating run finishes, then `results_3di.nc` and a run record exist under the
  archive folder and are still there after the 24-hour cleanup. The record holds `sim_id`, the rain input, the model
  revision, the graph hash, and the run timestamp. Where the DAG can read the model revision and the graph hash is
  unverified, so the story finds the source of each before it builds the record.
  Given test-rain mode (`FLOOD_TEST_RAIN_CSV` or `FLOOD_TEST_RAIN_MM_HR` set, read as `create_simulation.py` lines
  130 to 132 read them), then nothing is archived and the task logs that it skipped.
  Given a week of real-rain runs, then the daily growth in GB is measured and recorded in the plan. The estimate from
  `results` is about 7 MB per run (98 MB for 14 files), which is about 0.7 GB per day at 96 runs and is unverified
  against a real day.
  The archive folder is `D:\airflow_new_data\archive` (confirmed by the user on 2026-10-08), next to the data folder
  `D:\airflow_new_data\data` that `DATA_HOST_PATH` mounts (`compose.yml` line 61). It mounts at
  `/opt/airflow/archive` through a new `ARCHIVE_HOST_PATH` variable, with a default folder under the repository so
  the Mac and CI keep working.
  Given the archive folder, when the task runs, then it logs the free space of D: after each copy, and it fails the
  task loudly when the free space is below a floor, so a filling drive is never silent (the user asked for this on
  2026-10-08). The floor is a proposal: 50 GB, about 8 percent of the 586 GB that was free on 2026-10-08. The story
  confirms the number with the user. Two design points to settle before building: a full D: must not stop
  `9_build_flood_tiles` (give the archive task a trigger rule so the tile build still runs), and the cleanup must not
  delete a file the archive failed to copy (the cleanup is age-based at 24 hours, so a failed copy has that long to be
  retried or fixed).
  Estimate: M. The code is one task plus a compose mount, but the story also needs a server deploy and a check that
  needs real rain, which the replay cannot give. Priority: P1. Status: Not started. Sprint: 10 (see the dependency
  decision in the status history). Dependencies: none to build. It blocks `US-095` and `US-086`.
  Proof: a one-off run that reads the real Tomorrow.io forecast, with `FLOOD_TEST_RAIN_CSV` and `FLOOD_TEST_RAIN_MM_HR` unset, counts as the proof (the user, 2026-10-08). It does need the forecast to pass the rain gate (5 mm/h), so the proof waits for a forecast above it (the user chose this on 2026-10-08).
  Evidence: None yet.

- **Story 2 (US-095): Retire the `netcdf_values` ingest.**
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

## Open questions for the user

1. ~~Is `D:\airflow_new_data\archive` the right folder?~~ Confirmed by the user on 2026-10-08.
2. ~~Do `netcdf_files` and `netcdf_variables` on `storage-postgres` go with the retirement, or stay?~~ They go (the user, 2026-10-08).
3. After retirement, the `timescaledb` container holds only three empty tables. Retire the container too? This is a
   separate decision and nothing here decides it.
4. ~~What proves `US-094` if no real rain falls?~~ A one-off run with real rain counts as the proof (the user, 2026-10-08). The rain gate skips a run when the Tomorrow.io forecast is below `FLOOD_RAIN_THRESHOLD_MM_HR`, so the one-off run needs a forecast above the gate or a way to run one real-forecast simulation despite it. The user chose on 2026-10-08 to wait for a real forecast above the gate (option 1): no gate change and no override. So the proof waits for weather, and `US-095` and `US-086` wait with it.

## Status history

- **2026-10-08, draft.** Written at the user's request after decisions D-016 and D-018. The next free ID was `US-094`.
- **2026-10-08, draft.** `US-094` is in Sprint 10, the earliest sprint that satisfies the dependency of `US-095`
  (Sprint 11, the user's choice). This is a decision made by dependency under rule 3, and the user can override it.
- **2026-10-08, draft.** The user asked for a free-space check in `US-094` and for `netcdf_files` and `netcdf_variables` to be dropped in `US-095`. Open question 4 (what proves `US-094` without real rain) is still unanswered.
- **2026-10-08, draft.** The user decided a one-off real-rain run counts as the proof of `US-094`, so `US-095` does not wait for a storm. The one-off run must get past the rain gate, which is unsettled.
- **2026-10-08, draft.** The user chose option 1 for the rain gate: the proof of `US-094` waits for a real forecast above the gate. No gate change and no override. `US-095` and `US-086` wait for it.
