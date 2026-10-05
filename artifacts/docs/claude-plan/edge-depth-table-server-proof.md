---
date: 2026-10-05
type: plan
branch: front-end-according-to-mock-up
status: active
tags: [plan, sprint-8, edge-depth-table, us-045, timing, replay]
related: ["[[edge-depth-table]]", "[[edge-depth-table-stories]]", "[[edge-depth-table-airflow-task]]", "[[edge-depth-table-publish]]", "[[us-063-realistic-rain-replay-for-us-037-and-us-034]]", "[[sprint-plan-2]]", "[[flood-mapping-full-worker-concurrency-serializes-runs]]"]
---

# Plan: prove the edge depth table on the server (US-045)

## Context

Acceptance, from [[edge-depth-table-stories]] Story E7. Measure the build time, the file size, and the edge count of the table task on a real run on the server, check 20 edges against `ST_Value`, and record the numbers in [[edge-depth-table]], replacing the guessed size. If the build time exceeds the limit, log a blocker.

The limit (user, 2026-10-02): the table task runs beside the tile task, never delays it, and ends within 5 minutes of the end of `3_calculate_depth`.

Done before this plan: 42.0 s, 1,085,487 bytes, and 160 of 160 values equal, from a run of the build outside a DAG run (`server_check.sh`, 2026-10-05). What is missing is the same measure on real DAG runs, which needs the DAG unpaused. The Sprint 8 window (the 48-hour replay of [[us-063-realistic-rain-replay-for-us-037-and-us-034]], start `2026-10-05T15:15:00Z`) gives about 190 runs.

## What is measured

For every successful DAG run that simulated:

1. How long 9c ran, and when it ended relative to the end of `3_calculate_depth`. The limit is 5 minutes.
2. Whether 9c held up the tile task. The tile task becomes ready when `3_calculate_depth` ends. If 9c ran at any time between that and the start of the tile task, it took the worker first. This is exact with one worker slot (`AIRFLOW__CELERY__WORKER_CONCURRENCY=1`, see [[flood-mapping-full-worker-concurrency-serializes-runs]]) and a flag to read with the slot count in mind when there are more.
3. The size, edge count, and wet edges per step, from the XCom `edge_depth_table` that 9c pushes.
4. Whether 9c failed. A failure does not fail the DAG run (the `edge_table_done` leaf), so only this report shows it.

## Tools

- `scripts/edge_depth/table_timing.py`, tests first (26 tests, three changes make tests fail: an exclusive limit, a delay that is never flagged, and failures that are ignored).
- `scripts/edge_depth/table_timing.ps1` runs the query on `airflow-postgres` and pipes it to the script in the worker. The query ran on a mock of the Airflow tables in the cloud session (`dag_run`, `task_instance`, `xcom`), so the column names are an assumption until the first run on the server.
- The 20-edge spot check is `scripts/edge_depth/spot_check.py`, run on the newest table after the window.

## Steps after the unpause

1. Run `table_timing.ps1` after the first 4 or 5 runs. A failure there is found in minutes, not after 48 hours.
2. Run it again at the 24-hour and 48-hour readings of `US-069`.
3. Run `spot_check.py` on the newest table.
4. Write the numbers into [[edge-depth-table]], and close `US-045` with an evidence image of the report.

## Risks

- **The query is unverified on the real schema.** It was run on a mock. The first run on the server shows it.
- **One worker slot.** With one slot the table task can only run before or after the tile task and 9b, so a flagged delay is likely if 9c is ready before the tile task starts. That is the finding the story is for, and a blocker is logged if it happens.
- **`flood_on_roads` and 9c both follow 9b.** They compete for the worker too. The report measures 9c only.

## Status history

- **2026-10-05, active.** Plan written. `table_timing.py` and its 26 tests are done, and `table_timing.ps1` ran against a mock schema in the cloud session.
