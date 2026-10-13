---
date_drafted: 2026-10-13
type: user-story
us_id: "US-139"
title: "Skip a flood_mapping_full run whose slot is hours old"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Reviewed
kind: story
priority: P2
estimate: S
sprint: 
subsystem: airflow-pipeline, 3di-orchestration
source_ideas: []
related: ["[[3di-simulation-orchestration]]", "[[US-123-delete-flood-on-roads-and-flood-road-values|US-123]]", "[[decision-log|D-040]]"]
tags: [user-story]
---

# US-139 Skip a flood_mapping_full run whose slot is hours old

As the owner of the pipeline, I want a run of `flood_mapping_full` to do nothing when its slot is hours old, so an unpause or a long queue cannot revive old work.

On 2026-10-13 the owner unpaused the DAG, and a run from 2026-10-10 resumed at `3_calculate_depth`.
It published a run, the standing-flood rule saw that fresh publish, and the slots of 03:30 and 03:45 UTC started two real 3Di simulations with a forecast of 0 mm/h.
Each simulation costs 3Di compute, and the published run was three days old.
The story adds a guard to the tasks `0_check_forecast_rain`, `1_trigger_simulation`, `3_calculate_depth`, `3b_publish_depth_files`, and `9b_load_depth_raster`.
When the slot of the run (`run_slot`) is older than `FLOOD_STALE_RUN_MINUTES` (default 120, passed by `compose.yml`), the task raises `AirflowSkipException` with the slot, its age, and the limit, and the run ends with its tasks skipped.
The value 0 turns the guard off.
A run takes about 25 minutes from its slot to `9b`, so 120 minutes leaves room for a queue and a retry.

Given a run whose slot is 3 hours old, when one of the five tasks starts, then it is skipped with a message that names the slot, the age, and the limit, no simulation starts, and no depth file or tile is published.
Given a run whose slot is 20 minutes old, then the tasks run as before.
Given `FLOOD_STALE_RUN_MINUTES=0`, then no run is skipped.
Given a value that is not a whole number of minutes, then the DAG fails to parse with a message that names the variable.

Dependencies: None. Deploy it after the server steps of [[US-123-delete-flood-on-roads-and-flood-road-values|US-123]], because the guard would skip the frozen run of 03:45 UTC that the check of US-123 needs.

## Status history

- **2026-10-13, Ready.** Raised by the unpause of 2026-10-13 ([[US-123-delete-flood-on-roads-and-flood-road-values|US-123]]). It is in the backlog and has no `sprint`, as the product owner asked. The branch `us-139-stale-run-guard` is merged into `modular`.
- **2026-10-13, Reviewed.** Built and tested on the branch `us-139-stale-run-guard` (commit "Skip a flood_mapping_full run whose slot is hours old"), which is not merged into `modular` and not on the server (details items 1 to 5). The owner has not accepted it.
- **2026-10-13, Reviewed.** Merged into `modular` and pulled on the server on 2026-10-13. In the worker under real Airflow, `airflow tasks test` of `3_calculate_depth`, `3b_publish_depth_files`, and `9b_load_depth_raster` for a slot 7 hours old gave the state `skipped` with the message "Run slot 2026-10-13T03:00:00Z is 422 minutes old, over the limit of 120 minutes (FLOOD_STALE_RUN_MINUTES). Skipping so an old run does no work." and no traceback, before any work. A fresh run of the slot 10:00 UTC after the pull ran normally. `1_trigger_simulation` and `0_check_forecast_rain` were not tested on the server, because a failed guard there would start a real simulation or write a row. The owner has not accepted it.

## Evidence and details

**Evidence:** the test counts in details item 3. No screenshot.

**Details:**

1. `scripts/stale_run.py` holds the pure logic: `limit_minutes(env)` (default 120, digits only, else `ValueError` that names `FLOOD_STALE_RUN_MINUTES`), `age_minutes`, `is_stale` (false when the limit is 0), and `message`. A decorator `skip_stale_run` in `dags/flood_mapping_dag.py` raises `AirflowSkipException` before the task body, for `0_check_forecast_rain`, `1_trigger_simulation`, `3_calculate_depth`, `3b_publish_depth_files`, and `9b_load_depth_raster`. The limit is read once at parse time, so a bad value fails the import of the DAG, and a change needs a restart of the scheduler and the worker. `compose.yml` passes `FLOOD_STALE_RUN_MINUTES: ${FLOOD_STALE_RUN_MINUTES:-120}`.
   The message reads "Run slot 2026-10-13T03:00:00Z is 180 minutes old, over the limit of 120 minutes (FLOOD_STALE_RUN_MINUTES). Skipping so an old run does no work."
2. What a stale run does, read from the task graph and not run in Airflow. Stale at task 0: the tasks `1` to `9b` are skipped as downstream, and only the empty task `2c_archive_done` (rule `all_done`) shows success. Stuck at `3_calculate_depth` (a resumed run, as on 2026-10-10): the task skips, and `3b` and `9b` skip as downstream. Stuck at `3b` or `9b`: each has its own guard.
3. Tests: `python3 -m pytest -q test/` gives 136 passed and 1 skipped (129 before, with 7 new tests of the DAG), and `scripts/test_stale_run.py` gives 9 passed. The DAG tests cover a slot 180 minutes old (all five tasks skip, and the mocked simulation, download, publish, and tile-load functions record no call), a slot 20 minutes old (runs), exactly 120 minutes (runs), 121 minutes (skipped), the limit 0, the default of 120, and an invalid value (the import fails). The fake Airflow of the test module has a skip exception and defaults the limit to 0, because the other tests use fixed slots in the past.
4. In the worker, a bad value (`2h`) fails the parse of the DAG with "FLOOD_STALE_RUN_MINUTES must be a whole number of minutes, 0 or more, got '2h'" under Airflow's `DagBag`.
5. Not verified under real Airflow: how `AirflowSkipException` behaves inside `BranchPythonOperator`, and whether the run ends as `skipped` or `success` (the leaves are skipped, and Airflow usually marks such a run `success`, so the line "the run ends as skipped" of the story may not hold in the interface). `airflow tasks test` of Airflow 3 reads the live DAG bundle, so the check waits for the deploy: after the merge, `airflow tasks test flood_mapping_full 3_calculate_depth <date 6 hours old>` in the worker must show the skip before any work. Also not verified: `docker compose config`.

