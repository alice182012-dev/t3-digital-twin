---
date_open: 2026-09-28
date_closed: 2026-09-28
type: blocker
status: resolved
severity: P1
subsystem: airflow-pipeline
approaches_tried: 2
approaches_remaining: 0
tags: [blocker, airflow, celery, concurrency, fifteen-minute-cycle]
related: ["[[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]]", "[[fifteen-minute-cycle-tiles-and-histogram]]", "[[BL-009-hotstart-state-saved-at-end-of-run|hotstart-state-saved-at-end-of-run]]", "[[five-minute-tile-freshness]]", "[[us-037-narrow-the-per-run-critical-path]]"]
last_updated: 2026-09-28
---

# No Airflow pool separates the simulation trigger from the heavy pipeline tasks, so overlapping runs serialize and cascade

## Description

`airflow-worker` runs with `AIRFLOW__CELERY__WORKER_CONCURRENCY=2` (`.env`), and no task in
`dags/flood_mapping_dag.py` sets a `pool=`. Every task, light or heavy, competes for the same 2
Celery slots on the single worker container: a new run's `0_check_forecast_rain` and
`1_trigger_simulation` queue behind whatever the previous run's `3_calculate_depth`,
`9_build_flood_tiles`, `9b_load_depth_raster`, `3b_upload_netcdf_postgres`, and `flood_on_roads`
happen to be occupying.

Confirmed against a Stage 2 test of the fifteen-minute cycle (branch `fifteen-minute-cycle`) on
2026-09-28, with `FLOOD_TEST_RAIN_MM_HR=50` and `flood_mapping_full` unpaused on its 15-minute
schedule (`max_active_runs=2`):

| Run (slot) | First task starts | Last task ends | Duration |
| --- | --- | --- | --- |
| 04:00 | 04:11:57 (worker had just been recreated) | 04:32:38 | ~20:39 from trigger |
| 04:15 | 04:15:00 (on time) | 04:37:54 | ~20:00 from trigger |
| 04:30 | 04:32:40 | failed (`3_calculate_depth`), killed by the user | — |
| 04:45 | 04:47:31 (ran alone, no overlap) | 05:04:48 | 17:17 |
| 05:00 | 05:02:11 | 05:32:35 | ~30:24 |
| 05:15 | 05:16:58 | 05:52:22 | ~35:24 |
| 05:30 | 05:32:36 | 05:57:55 | ~25:19 |

The 05:00 run's `0_check_forecast_rain` didn't start until 05:02:11.42 — the same second the
04:45 run's very last task, `flood_on_roads`, finally finished at 05:02:11.34. Both worker slots
were occupied by the 04:45 run's own tasks the entire time, so the 05:00 run's first task, a
sub-two-second rain check, sat queued rather than running immediately. Once two runs are both
active, each subsequent run pays for the previous one's entire remaining pipeline, not just its
simulation trigger, and the delay compounds: 04:45 solo took 17:17, but by 05:15 (with 05:00 and
05:15 both active) a run took 35:24, almost double.

`scripts/create_simulation.py`'s `run_forecast_process` (called by `1_trigger_simulation`) is not
the cause. It creates a new 3Di simulation, attaches the hotstart state, loads rain, registers
saved states, sends `start`, and calls `monitor_simulation()`, which polls until the simulation's
status genuinely reaches `"finished"` before the task returns. Nothing in that code checks whether
another simulation is active, or holds any lock against 3Di itself. `1_trigger_simulation`'s
duration was a consistent ~3 minutes across every run in this test (04:45: 3:01, 05:00: 3:01,
05:15: 3:13, 05:30: 3:01), so 3Di is free again well before the next run's trigger even gets a
worker slot to run on.

## Why this matters

The fifteen-minute cycle ([[fifteen-minute-cycle-tiles-and-histogram]]) assumes each run's tiles
for step 1 publish with a few minutes of margin before that step becomes "now"
([[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]]'s proposed design: tiles by about +11:30, step 1 becomes now at
+15:00). Under two genuinely overlapping runs, tiles instead publish around +20 minutes, already
past the point they were supposed to be live, and the delay keeps growing the longer overlapping
runs continue. This turns risk 3 in [[fifteen-minute-cycle-tiles-and-histogram]] ("tiles, raster
load, and flood on roads overlapped... their contention at 8 steps is not measured") from a
same-run contention question into a cross-run one, and the cross-run answer is worse: the whole
downstream pipeline of one run blocks the next run's simulation trigger, not just its own
same-run tasks.

## Approaches tried

### Approach 1

Candidate 1 from Decision and explanation: a dedicated `threedi_trigger` pool (2 slots) for
`0_check_forecast_rain` and `1_trigger_simulation`. Two false starts before it worked:

1. Self-provisioned the pool at DAG-parse time (`16bcf44`). Deployed; DAG parsed with no import
   errors, but the pool never appeared. Root cause: the `Pool()` insert omitted `include_deferred`,
   a `NOT NULL` column with no ORM-side default in this Airflow version, so every insert raised
   `psycopg2.errors.NotNullViolation`, silently caught by the surrounding `try/except`.
2. Fixed by passing `include_deferred=False` explicitly (`c14e55d`). Deployed; still no pool.
   Checked the per-DAG parse log directly (`/opt/airflow/logs/dag_processor/<date>/dags-folder/
   flood_mapping_dag.py.log`, not the container's main stdout) and found the real cause: Airflow 3
   forbids direct ORM or database access from code that runs at DAG-parse time at all
   ("Direct database access via the ORM is not allowed in Airflow 3.0"). No `Pool()` call at
   module scope could ever have worked here, independent of the `include_deferred` bug.
3. Dropped the self-provisioning function entirely (`2467c50`). Created the pool once instead with
   `airflow pools set threedi_trigger 2 "3Di rain-check and simulation trigger tasks"`, run by hand
   on the server, the same way this repo's schema scripts are run once against a fresh deploy
   rather than from inside a DAG file. Confirmed: `airflow pools list` shows `threedi_trigger` with
   2 slots and the right description, `airflow dags list-import-errors` reports nothing, and both
   `0_check_forecast_rain` and `1_trigger_simulation` reference `POOL_THREEDI_TRIGGER` in the
   deployed file.

### Approach 2

Candidate 2, revisited after the live re-test showed Approach 1 alone doesn't fix the heavy tasks'
own contention (see the 2026-09-28 "monitoring" entry in Status history: three overlapping runs, a
14:30 tile still served at 14:37). Original objection was that raising
`AIRFLOW__CELERY__WORKER_CONCURRENCY` lets two `3_calculate_depth` tasks run at once, up to 16
`threedidepth` subprocesses competing for the server's actual capacity. Checked that capacity
directly: `Get-CimInstance Win32_Processor` and `docker info` show 6 physical cores, 12 logical
processors, 16 GB RAM visible to Docker. `3_calculate_depth` is the only heavy task with real
CPU-bound multiprocessing (`MAX_WORKERS=8` subprocesses); `9_build_flood_tiles` only uses
`FLOOD_EXTENT_WORKERS=2` threads, and `9b_load_depth_raster`, `flood_on_roads`, and the netcdf
upload are DB or I/O-bound with no worker pool of their own. So the actual risk is narrow: two
concurrent `3_calculate_depth` tasks would want 16 processes on 12 logical cores (oversubscribed,
and CPU-bound oversubscription typically makes both runs slower than running them one at a time,
not just proportionally slower).

Revised plan: raise `AIRFLOW__CELERY__WORKER_CONCURRENCY` (to 4) for real added throughput on the
lighter tasks and the trigger chain, paired with a new `depth_calc` pool (1 slot) holding only
`3_calculate_depth`, so at most one depth-calc ever runs at once regardless of how many runs
overlap. Same pattern as Approach 1's pool, applied to the one task that can actually oversubscribe
the box. Not yet implemented.

## Decision and explanation

Candidate 1, done (see Approaches tried, Approach 1). Candidate 2, revised and in progress (see
Approach 2): pairing it with a dedicated `depth_calc` pool removes the original objection instead of
just accepting the risk. Two original candidates, for the record:

1. Give the rain-check and simulation-trigger tasks their own Airflow pool (for example
   `threedi_trigger`, 1 to 2 slots), separate from the heavy GIS and DB tasks. That chain is
   I/O-bound (waiting on 3Di and Tomorrow.io), not CPU-bound, so it doesn't need to compete with
   `3_calculate_depth` (which already spawns `MAX_WORKERS=8` subprocesses) for the same slots. This
   lets a new run's simulation start as soon as 3Di and the worker's dedicated slot are free,
   regardless of how far behind the previous run's downstream processing is.
2. Raise `AIRFLOW__CELERY__WORKER_CONCURRENCY` instead. Simpler, but it also lets two heavy tasks
   like `3_calculate_depth` run at once (up to 16 total subprocesses on one host), which is a
   different and riskier change than the current single-heavy-task-at-a-time behavior this server
   has been running under.

The first candidate is likely safer: it targets the actual bottleneck (the trigger chain being
gated behind unrelated heavy work) without changing how many heavy tasks can run at once.

## Concerns

A pool fixes queuing for the *trigger* chain, but doesn't by itself fix the heavy downstream tasks
still taking longer under genuine two-run overlap (Celery concurrency=2 still caps how many of
those run at once). It buys the simulation trigger a guaranteed slot, not a faster pipeline. Confirm
after the fix whether tiles for step 1 still publish within the design's margin once two runs
overlap, or whether the heavy-task queuing also needs its own pool or more worker capacity.

The pool is now a manual, out-of-band deploy dependency: `airflow pools set threedi_trigger 2
"3Di rain-check and simulation trigger tasks"` has to be run once against any environment this DAG
deploys to (a fresh server, a rebuilt metadata DB), since it's no longer self-provisioned. Nothing
in the repo runs this automatically today. If this DAG is ever deployed somewhere new, this step is
easy to forget, and forgetting it means the trigger chain's tasks queue forever: a task that
references a pool name with no matching row gets no slots at all, it doesn't fall back to the
default pool.

## Related topics

- [[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]], the "Risks to measure" section and its Stage 2 test result
- [[fifteen-minute-cycle-tiles-and-histogram]], risk 3
- [[BL-009-hotstart-state-saved-at-end-of-run|hotstart-state-saved-at-end-of-run]], since a run that's still queued behind another run's
  heavy tasks is also a run whose hotstart state timing assumptions shift

## Status history

- **2026-09-28, open.** Found during the fifteen-minute cycle's Stage 2 test (two overlapping runs
  under `FLOOD_TEST_RAIN_MM_HR=50`). Confirmed against `dags/flood_mapping_dag.py` (no `pool=` on
  any task) and `scripts/create_simulation.py` (`monitor_simulation` blocks until 3Di reports
  `"finished"`, no cross-run lock). `flood_mapping_full` re-paused and the test rain variable
  unset after the test.
- **2026-09-28, monitoring.** Candidate 1 built and deployed to `main` (`c14e55d`, on top of
  `16bcf44`): a `threedi_trigger` pool (2 slots) holding `0_check_forecast_rain` and
  `1_trigger_simulation`, self-provisioned at DAG-parse time, every other task unchanged. Deploying
  this also moved the server from tracking `fifteen-minute-cycle` to `main`, since local `main` had
  already absorbed that branch's work in an earlier session but had never been pushed; `main` is a
  strict superset, not a regression (`dags/test_dag.py` correctly gone, `flood_mapping_dag.py`
  present, no import errors). Live verification caught a second bug the offline worktree couldn't
  see: the pool insert failed every parse with `psycopg2.errors.NotNullViolation` on
  `slot_pool.include_deferred` (no ORM-side default in this Airflow version), silently swallowed by
  the surrounding `try/except` and only logged.
- **2026-09-28, monitoring.** Fixed `include_deferred` (`c14e55d`). Still no pool after several
  parse cycles. Found the per-DAG parse log (not the container's main stdout) records a different,
  unfixable-in-place error every parse: Airflow 3 forbids ORM or database access from DAG-parse-time
  code entirely. Dropped the self-provisioning function (`2467c50`) and created the pool once by
  hand instead (`airflow pools set threedi_trigger 2 "..."`). Confirmed on the server:
  `airflow pools list` shows `threedi_trigger`, 2 slots, correct description; `airflow dags
  list-import-errors` reports nothing; both tasks reference the pool in the deployed file. Not yet
  confirmed: a fresh overlap test showing the trigger chain no longer queues behind the heavy
  tasks, and updating the deploy steps in [[fifteen-minute-cycle-tiles-and-histogram]] or a similar
  deploy doc to include the `pools set` command so a future fresh deploy doesn't silently miss it.
- **2026-09-28, monitoring.** Live re-test under `FLOOD_TEST_RAIN_MM_HR=50` confirmed the trigger
  pool works: a new run's `1_trigger_simulation` no longer queues behind a previous run's heavy
  tasks. But with three runs overlapping, the heavy tasks' own contention with each other is
  unchanged: the frontend served a 14:30 tile at 14:37 local (7 minutes stale) because the run that
  should have refreshed it was still mid-`9_build_flood_tiles`. Captured as
  [[five-minute-tile-freshness]], which also names a separate, structural point independent of this
  blocker: even a fully fixed pipeline can't guarantee under 5 minutes of staleness on the current
  15-minute tile grid, only 0 to 15 minutes.
- **2026-09-28, monitoring.** Approach 2 built and deployed (`26b6133`): `3_calculate_depth` now
  runs in its own single-slot `depth_calc` pool, and `AIRFLOW__CELERY__WORKER_CONCURRENCY` raised
  from 2 to 4. Deploy done with the DAG paused and no run in flight (confirmed via
  `dags list-runs` before touching anything). Confirmed on the server: the container's env shows
  concurrency 4, `airflow pools list` shows both `threedi_trigger` (2 slots) and `depth_calc`
  (1 slot), `airflow dags list-import-errors` reports nothing. Not yet confirmed: a fresh overlap
  test showing the heavy tasks actually finishing faster under real contention, and that two
  `3_calculate_depth` tasks never run concurrently under the new pool.
- **2026-09-28, resolved.** Reviewed four consecutive real runs after the deploy (08:45, 09:00,
  09:15, 09:30, all under sustained rain). Both fixes confirmed live: every run's
  `1_trigger_simulation` started within seconds of its rain check, zero queuing behind a previous
  run's heavy tasks, even while that run was still actively processing. No two `3_calculate_depth`
  tasks ever overlapped; the one observed handoff waited only 19 seconds for the `depth_calc` slot.
  The cascading blowup this blocker is named for is gone: durations that previously grew run over
  run (17, 32, 37, 25 minutes under the old config) are now flat at a consistent 17 to 18 minutes.
  Residual gap, now a latency question rather than a contention one: each run's own critical path
  (trigger about 3.5 min, depth-calc about 7 min, raster load about 2.3 min, tile build about
  6 min) adds to a bit more than the 15-minute cycle, so a step's tile still publishes 1.5 to 3
  minutes after its target moment instead of the design's intended margin before it. Tracked
  separately in [[five-minute-tile-freshness]] (candidate D, and the streaming depth-calc/tile-cut
  idea discussed the same day), since it's no longer about runs serializing against each other.
- **2026-10-05, resolved.** A later retest (the `US-063` 48-hour real-rain replay, 2026-10-02 to
  2026-10-04, analyzed in [[us-037-narrow-the-per-run-critical-path]]) measured the same critical
  path this blocker's baseline covers, this time against real Hanoi rain instead of a constant
  50 mm/h stress case. Confirmed no overlap between consecutive runs' `9_build_flood_tiles` tasks
  anywhere in the window, meaning this blocker's fix held under a multi-day real test, not just the
  four-run check it closed on. The new numbers aren't directly comparable to this page's baseline
  (lighter real rain against a constant storm, less flooded area, less compute per stage), but they
  confirm the fix itself didn't regress. The residual latency question this page handed off still
  isn't settled: `9_build_flood_tiles` grew 4.8x over the 48 hours (90.9 s to 439.4 s) with no
  cross-run overlap to explain it, so something else is driving it. See
  [[us-037-narrow-the-per-run-critical-path]] for the full numbers and the open follow-up.
