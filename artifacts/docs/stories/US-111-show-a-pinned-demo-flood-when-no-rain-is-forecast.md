---
date_drafted: 2026-10-10
type: user-story
us_id: "US-111"
title: "Write the forecast mode status row (part one of the pinned demo flood)"
epic: "[[EP-17-flood-data-pipeline-and-core-output|EP-17]]"
status: Done
kind: story
priority: P2
estimate: S
sprint: 14
subsystem: flood-extent
source_ideas: []
related: ["[[decision-log|D-030]]", "[[decision-log|D-013]]", "[[minio-flood-extent-pipeline]]", "[[core-output-contract]]", "[[edge-depth-table-format]]", "[[US-088-cut-the-hanoi-storm-of-2026-09|US-088]]", "[[US-102-replay-the-storm-with-the-us-101-fix-to|US-102]]"]
tags: [user-story]
---

# US-111 Write the forecast mode status row (part one of the pinned demo flood)

As a visitor who opens the flood map on a day with no forecast rain, I want the map, the routing, and the depth popup to use a pinned demo flood with a warning, so the map has a flood to show when the simulation has none.

The flood map has three modes, set by the rain forecast from Tomorrow.io ([[decision-log|D-013]]) and the steps the simulation has published ([[decision-log|D-030]]).

- **LIVE:** rain is forecast above the threshold, or a standing flood exists, and real simulation steps are published. The map shows the real result, as today.
- **PENDING:** rain is forecast, but the simulation has published no step yet. The map shows a dry map with a warning that the simulation is running.
- **DEMO:** no rain is forecast past the threshold and no flood stands. The map shows the demo flood with the warning "No flood forecasted, displaying the demo flood of Sep 16, 2026", in English only.

The demo is one static frame, the peak step of the 12-hour replay of the 2026-09-16 storm ([[US-088-cut-the-hanoi-storm-of-2026-09|US-088]]).
It has no slider and no animation.

Given no rain is forecast past the threshold and no flood stands, when a visitor opens the flood map, then the map shows the pinned demo flood and the warning "No flood forecasted, displaying the demo flood of Sep 16, 2026".

Dependencies: [[US-102-replay-the-storm-with-the-us-101-fix-to|US-102]] ran the replay that supplies the peak step.
The DAG was not changed while that replay ran.

## Split

The story was an L, so it was split on 2026-10-12, as [[scrum-framework]] requires.
This story is part one, the status row, and its estimate is S.
The other parts have their own IDs:

- [[US-129-pin-the-peak-step-of-the-demo-flood|US-129]] pins the peak step so that no prune removes it (M).
- [[US-130-serve-the-forecast-mode-and-read-the-pinned-step|US-130]] serves the mode and reads the pinned step in the backend (M).
- [[US-131-show-the-demo-flood-banner-and-the-pinned-frame|US-131]] shows the banner and the pinned frame in the frontend (M, backlog, not backend).

## Part one: the status row

Task `0_check_forecast_rain` already decides the rain gate for each run.
This part writes that decision to a table, so the backend can read it.
The table holds one row per decision: the time, the forecast peak in mm/h, the gate in mm/h, whether a flood stands, and the mode (`LIVE`, `PENDING`, or `DEMO`).
The mode follows the definitions at the top of this story.
The table is a contract table: it goes on [[core-output-contract]] and in the `routing_reader` list, or the backend gets `permission denied`.
The signal is a proposal of the first draft, and this part confirms it or changes it.

Given a run of `flood_mapping_full` with rain above the gate, when `0_check_forecast_rain` ends, then the status table has a row for that decision with mode `PENDING` until the first step is published, and `LIVE` after.
Given a decision with no rain above the gate and no standing flood, then the row has mode `DEMO`.
Given the role `routing_reader`, then it can read the table, and a write fails with a permission error.

## Acceptance check

On the server, after the change is pulled.
Read the newest status row with `psql`, and take a screenshot of the query result and of the contract page entry.

1. Given the table, when a gate decision runs, then one row holds the mode, the forecast peak, the gate, and the standing-flood flag.
2. Given `routing_reader`, then `SELECT` works and an `INSERT` fails.

## Status history

- **2026-10-10, draft.**
  Written from decision [[decision-log|D-030]].
  No code is written, and no branch holds the feature.

- **2026-10-12, Ready.** Split into four stories at the product owner's request, and this part is picked for [[SPR-014-finish-the-remaining-backend|SPR-014]]. The plan of the original story moved to the parts.
- **2026-10-12, Reviewed.** Part one is built and tested, not deployed. Table `forecast_mode` holds one row per gate decision (`slot`, `decided_at`, `rain_peak_mm_hr`, `gate_mm_hr`, `standing_flood`, `mode`). Task `0_check_forecast_rain` writes it, and `9b_load_depth_raster` moves its run's row from `PENDING` to `LIVE`. The mode is `DEMO` when the gate is closed, `LIVE` when it is open and a `depth_raster` row of `flood_run_output` is younger than 45 minutes, and `PENDING` otherwise. `standing_flood` is NULL when the forecast rain alone opened the gate, because the task does not read the flood then. A failed write is printed and stops neither the gate nor `9b`. The table is on [[core-output-contract]] and in the `routing_reader` list. 9 tests in `scripts/test_forecast_mode.py` pass against a throwaway PostGIS, and the DAG tests cover the gate and the move to `LIVE`. Still open: the pull on the server, a `psql` read of the newest row, the `INSERT` that `routing_reader` is refused, and the screenshot.
- **2026-10-13, Done.** The product owner accepted it after the server check. The evidence is the output file `US-111-server-forecast-mode-2026-10-13.txt`.

## Evidence and details

**Evidence:** `artifacts/docs/stories/evidence/US-111-server-forecast-mode-2026-10-13.txt`, the output of the two `psql` commands that the owner ran against the server on 2026-10-13.

**Details:**

1. The server is on head `458352c` after `git pull --ff-only alice modular`.
   Airflow lists no import error, and `check_tables.py` says `FRESH`.
2. `create_forecast_mode_table.py` ran in the worker and made `forecast_mode`.
   `create_routing_reader_role.py routing_reader` ran there too.
   The worker mounts neither `core_contract.py` nor the contract page, so both were copied to the worker's `/tmp` for the run and removed afterwards.
   The role now reads `forecast_mode` and `demo_pin`.
3. `flood_mapping_full` is paused, so no scheduled run wrote a row.
   `airflow tasks test flood_mapping_full 0_check_forecast_rain` ran in the worker.
   The row has slot `2026-10-13 02:45:00`, forecast peak 0, gate 5, `standing_flood` false, and mode `DEMO`.
4. The same task run in the scheduler container wrote a gate of 0.01, because `FLOOD_RAIN_THRESHOLD_MM_HR` is 0.01 there and 5 in the worker.
   Real runs execute in the worker.
   The test ran again in the worker, and it replaced the row of the same slot.
5. `routing_reader` reads the newest row, and its `INSERT` fails with `permission denied for table forecast_mode`.
6. Not tested on the server with a real run: the move of a row from `PENDING` to `LIVE` by `9b_load_depth_raster`, which needs a cold start with a forecast above the gate.
   The DAG tests cover it, and item 8 covers the functions on the server.
7. The three modes were read through the backend with a temporary row of slot `2030-01-01`, which was deleted afterwards ([[US-130-serve-the-forecast-mode-and-read-the-pinned-step|US-130]]).
8. On 2026-10-13, in the worker and against a scratch database (`us111_scratch_test`, dropped afterwards), the functions of the two tasks gave the expected modes (`evidence/US-111-pending-to-live-scratch-db-2026-10-13.txt`).
   `record_decision` with the gate open and no published raster gave `PENDING`.
   After `run_output.record` wrote the `depth_raster` row, `mark_live` changed the row and the mode read `LIVE`.
   A second `mark_live` changed nothing.
   The next decision with a raster younger than 45 minutes gave `LIVE` at once, as the real runs of 03:30 and 03:45 UTC did.
   This checks the functions and not the DAG task.

