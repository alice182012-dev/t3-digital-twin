---
date_drafted: 2026-10-08
type: user-story
us_id: "US-094"
story_label: "1"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Reviewed
priority: P1
estimate: M
sprint: 
subsystem: core-output
related: ["[[EP-15-archive-and-netcdf-retirement]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
title: "Archive `results_3di.nc` and a run record to D: when the pipeline reads real rain"
---

# US-094 Archive `results_3di.nc` and a run record to D: when the pipeline reads real rain

As the owner of the case-study data, I want each real-rain simulating run's result file kept on D:, so a past storm can be analyzed after the 24-hour cleanup deletes `RESULT_DIR`.
Given the DAG as it is, the cleanup runs inside `9_build_flood_tiles`: `publish.publish_run` receives
`cleanup_dirs=[RESULT_DIR, DEPTH_ROOT_DIR, FLOOD_EXTENT_WORK_DIR]` (`dags/flood_mapping_dag.py` line 251) and the age limit `FLOOD_EXTENT_CLEANUP_MAX_AGE_HOURS` (24).
Task `2_download_results` writes
`RESULT_DIR/<sim_id>/results_3di.nc`.
The new task copies that file after `2_download_results`, and `9_build_flood_tiles` waits for it, so the copy cannot race the cleanup.
The task runs in parallel with `3_calculate_depth` and is not on the critical path.
Given real-rain mode, when a simulating run finishes, then `results_3di.nc` and a run record exist under the archive folder and are still there after the 24-hour cleanup.
The record holds `sim_id`, the rain input, the model revision, the graph hash, and the run timestamp.
Where the DAG can read the model revision and the graph hash is unverified, so the story finds the source of each before it builds the record.
Given test-rain mode (`FLOOD_TEST_RAIN_CSV` or `FLOOD_TEST_RAIN_MM_HR` set, read as `create_simulation.py` lines
130 to 132 read them), then nothing is archived and the task logs that it skipped.
Given a week of real-rain runs, then the daily growth in GB is measured and recorded in the plan.
The estimate from `results` is about 7 MB per run (98 MB for 14 files), which is about 0.7 GB per day at 96 runs and is unverified against a real day.
The archive folder is `D:\airflow_new_data\archive` (confirmed by the user on 2026-10-08), next to the data folder
`D:\airflow_new_data\data` that `DATA_HOST_PATH` mounts (`compose.yml` line 61).
It mounts at `/opt/airflow/archive` through a new `ARCHIVE_HOST_PATH` variable, with a default folder under the repository so the Mac and CI keep working.
Given the archive folder, when the task runs, then it logs the free space of D: after each copy, and it fails the task loudly when the free space is below a floor, so a filling drive is never silent (the user asked for this on 2026-10-08).
The floor is a proposal: 50 GB, about 8 percent of the 586 GB that was free on 2026-10-08.
The story confirms the number with the user.
Two design points to settle before building: a full D: must not stop
`9_build_flood_tiles` (give the archive task a trigger rule so the tile build still runs), and the cleanup must not delete a file the archive failed to copy (the cleanup is age-based at 24 hours, so a failed copy has that long to be retried or fixed).
Estimate: M.
The code is one task plus a compose mount, but the story also needs a server deploy and a check that needs real rain, which the replay cannot give.
Priority: P1.
Status: Reviewed.
Sprint: 10 (see the dependency decision in the status history).
Dependencies: none to build.
It blocks `US-095` and `US-086`.
Proof: a one-off run that reads the real Tomorrow.io forecast, with `FLOOD_TEST_RAIN_CSV` and `FLOOD_TEST_RAIN_MM_HR` unset, counts as the proof (the user, 2026-10-08).
It does need the forecast to pass the rain gate (5 mm/h), so the proof waits for a forecast above it (the user chose this on 2026-10-08).
Evidence: None yet.

## Status history

- **2026-10-09, active.** Built on `modular`, not pushed and not deployed (no pull on the server during the second replay).
  `scripts/archive_results.py` copies `results_3di.nc` and `run_record.json` to `<ARCHIVE_DIR>/<sim_id>/` through a temporary file, so a second run gives the same archive.
  The record holds `sim_id`, `run_timestamp`, `rain_input`, `model_id` (from `MODEL_ID`), `graph_hash` (from `graph.json` of the graph export, null without it), `bytes`, and `sha256`.
  Task `2b_archive_results` runs after `2_download_results` and skips when the rain source is not `tomorrow.io`.
  A join task `2c_archive_done` with trigger rule `all_done` sits between it and `9_build_flood_tiles`, so a failed archive turns only `2b` red and the tile build still runs.
  `compose.yml` mounts `ARCHIVE_HOST_PATH` (default `./archive`) at `/opt/airflow/archive`, and `ARCHIVE_MIN_FREE_GB` defaults to 50.
  Tests: 9 in `scripts/test_archive_results.py` and 15 in `test/test_flood_mapping_dag_graph.py` pass.
  Still open: the deploy (set `ARCHIVE_HOST_PATH=D:\airflow_new_data\archive` in the server `.env`), the real-rain proof, the daily growth in GB, and your confirmation of the 50 GB floor.
- **2026-10-10, carried from the retired TODOS note.** 24 tests pass for `scripts/archive_results.py`, task `2b_archive_results`, and the join task `2c_archive_done`.
