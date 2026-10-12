---
date_drafted: 2026-10-08
type: user-story
us_id: "US-094"
story_label: "1"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Ready
kind: story
priority: P1
estimate: S
sprint: 13
subsystem: core-output
related: ["[[EP-15-archive-and-netcdf-retirement]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[US-114-prove-the-real-rain-archive-and-measure-growth|US-114]]"]
title: "Deploy the archive mount and show the test-rain skip"
---

# US-094 Deploy the archive mount and show the test-rain skip

As the owner of the case-study data, I want the archive folder on D: mounted into the Airflow worker and the test-rain skip shown, so that the real-rain archive has a folder to write into.

This is part one of the original story.
The archive code is built: `scripts/archive_results.py`, the task `2b_archive_results`, and the join task `2c_archive_done` (see the status history).
This part deploys the mount and shows that test-rain mode skips the copy.
The copy itself, the free-space log, the 50 GB floor check, the run record on a real run, and the growth in GB move to [[US-114-prove-the-real-rain-archive-and-measure-growth|US-114]], because only a real-rain run exercises them.

Given the server `.env` with `ARCHIVE_HOST_PATH=D:\airflow_new_data\archive`, when the worker is recreated, then `docker exec airflow_new-airflow-worker-1 ls /opt/airflow/archive` lists the folder.
Given test-rain mode (`FLOOD_TEST_RAIN_CSV` or `FLOOD_TEST_RAIN_MM_HR` set, read as `create_simulation.py` lines 130 to 132 read them), when a simulating run finishes, then `2b_archive_results` logs that it skipped, `2c_archive_done` ends `success`, and `9_build_flood_tiles` still runs.

Dependencies: none to build.

**Evidence so far.** Rendered output of read-only queries on the server, captured 2026-10-10 18:40 +07 from the Mac.
It shows the `2b_archive_results` log line of three sampled runs, the task states of all 58 replay runs, and the archive mount in the worker.

![[us-094-test-rain-skip-output.png|900]]

## Status history

- **2026-10-09, active.** Built on `modular`, not pushed and not deployed (no pull on the server during the second replay).
  `scripts/archive_results.py` copies `results_3di.nc` and `run_record.json` to `<ARCHIVE_DIR>/<sim_id>/` through a temporary file, so a second run gives the same archive.
  The record holds `sim_id`, `run_timestamp`, `rain_input`, `model_id` (from `MODEL_ID`), `graph_hash` (from `graph.json` of the graph export, null without it), `bytes`, and `sha256`.
  Task `2b_archive_results` runs after `2_download_results` and skips when the rain source is not `tomorrow.io`.
  A join task `2c_archive_done` with trigger rule `all_done` sits between it and `9_build_flood_tiles`, so a failed archive turns only `2b` red and the tile build still runs.
  `compose.yml` mounts `ARCHIVE_HOST_PATH` (default `./archive`) at `/opt/airflow/archive`, and `ARCHIVE_MIN_FREE_GB` defaults to 50.
  Tests: 9 in `scripts/test_archive_results.py` and 15 in `test/test_flood_mapping_dag_graph.py` pass.
- **2026-10-10, carried from the retired TODOS note.** 24 tests pass for `scripts/archive_results.py`, task `2b_archive_results`, and the join task `2c_archive_done`.
- **2026-10-10, deployed on the server.** `ARCHIVE_HOST_PATH` is set on the server, and the worker mounts the archive folder.
- **2026-10-10, reviewed.** During the storm replay of [[US-102-replay-the-storm-with-the-us-101-fix-to|US-102]] with the test-rain setting on, `2b_archive_results` logged the skip in the three sampled runs, and 58 of 58 `2b` and `2c` tasks ended `success`.
  The archive mount exists in the worker and holds 0 files.
- **2026-10-12, Ready.** Split at Sprint 13 planning. This part is the deploy and the test-rain skip, and it is sized S (2 points). The real-rain proof, the copy, the floor, and the growth are [[US-114-prove-the-real-rain-archive-and-measure-growth|US-114]], in the backlog.

## Evidence and details

Fill this when the story reaches `Done`.
The evidence above is the 2026-10-10 capture.
