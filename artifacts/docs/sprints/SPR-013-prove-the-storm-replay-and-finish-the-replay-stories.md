---
date: 2026-10-10
type: sprint
sprint_id: "SPR-013"
sprint: 13
start_date: 2026-10-12
end_date: 2026-10-25
status: planning
tags: [sprint]
related: ["[[scrum-framework]]", "[[Velocity]]", "[[decision-log|D-024]]"]
---

# SPR-013 Sprint 13: prove the storm replay and finish the replay stories

The first sprint under Scrum ([[decision-log|D-024]]). It runs two weeks, from Monday 2026-10-12 to Sunday 2026-10-25 ([[decision-log|D-026]]). Planning is on 2026-10-12. This file holds a proposal until the product owner confirms the goal and the picks. [[TODOS]] shows the sprint in the terminal.

## Sprint goal

Proposed: the pipeline passes a full-storm replay with the `US-101` fix, and the stories that read that replay (`US-089` and `US-091`) are `Done`.

## Planning

- **Velocity.** The last three sprints gave 7, 15, and 25 points ([[Velocity]]). Those sprints lasted days, not two weeks, so they under-measure a two-week sprint. A planning range is 16 points (the average) to 25 points (the best of the three). The product owner sets the forecast on Monday, and Sprint 13 calibrates the next one.
- **Proposed picks.** `US-102` (S, P0), `US-089` (M, P1), and `US-091` (M, P1) make 8 points. They share one replay of about 13.5 hours (see "How to close the proposed picks"), so the replay is the critical path and starts on Monday.
- **Room for 8 to 17 more points.** The ready stories with no dependency on the replay are `US-076` (M), `US-085` (S), `US-079` (XS), and `US-080` (XS), which are frontend recheck rows (7 points). Other `Ready` stories can fill the rest after refinement. The product owner said on 2026-10-08 that routing finishes first, so these are the product owner's choice.
- **Work in progress.** At most two stories are `In progress` at once. `US-102` starts first on Monday, because the replay is the longest wait.
- **Not picked.** `US-094` waits for real rain above 5 mm/h and cannot finish this sprint.

**Open decisions for the product owner at planning:**

1. Confirm the goal and the picks above. Setting `sprint: 13` on a story is the pick.
2. Give the go for the replay. The scope is decided: A, the full storm (the user, 2026-10-10).
3. Set the pause time of the replay. The recommendation is 00:15 on Tuesday 2026-10-13.
4. Accept the rewritten hotstart check and the wet-edge ratio band of 0.8 to 1.25 for `US-102`.
5. Choose 30 or 60 pairs for `US-091`. The recommendation is 60, about 31 minutes.
6. Confirm the 50 GB free-space floor, split `US-094`, and decide whether a lowered rain gate may prove the archive if no forecast passes 5 mm/h by 2026-10-23.
7. Decide whether `TIME_AWARE_ROUTING` goes on for good (`rollout.ps1 -LeaveOn` and `TIME_AWARE_ROUTING=true` in `.env`).
8. The product owner resolved [[BL-023-9c-sampling-step-runs-over-770-seconds|BL-023]] on 2026-10-10 (answer: yes). The question was whether it resolves if the replay shows a longest `9c` under 120 s.

## How to close the proposed picks

Analysis of 2026-10-10 by a read-only subagent.
I checked its main claims against the code: `compose.yml` line 38, the `[Hotstart` and `[Coldstart` log strings in `create_simulation.py`, the `stop` read-back in `replay.ps1`, the 45-minute limit in `standing_flood.py`, and the wall-clock departure in the backend.
The 37, 12, and 9 unit tests of `rain_replay`, `standing_flood`, and `archive_results` pass.

**What the analysis found**

- One replay can close `US-102`, `US-091`, and `US-089`, and it can also deploy the `US-094` mount and show its test-rain skip.
- The "about 12 hours" of `US-102` is wrong.
  The last table of the second replay still forecasts 2,276 edges at 5 cm or more and a 563 cm maximum.
  The standing-flood rule will not stop on its own, so the owner sets a pause time.
- The hotstart clause of `US-102` would pass without proof, because with the flood standing there is no quiet stretch.
  The real test is that the five slots at event offsets 6h to 7h each log `[Hotstart` and never `[Coldstart] No saved state`.
- "Close to the forecast" needs a number.
  Proposal: wet edges at the first valid time of each former-gap run are 0.8 to 1.25 times the previous run's forecast for that time.
  The second replay gave about 0.30.
- The sticky check of `US-091` cannot run on old tables, because the backend departs at the later of the step time and now.
  It runs live during the replay with `TIME_AWARE_ROUTING` on, and the single-timestep run follows with it off.
  The same live run can resolve [[BL-026-sticky-closure-clock-anchored-at-floored-departure|BL-026]].
- The dependency of `US-091` is `US-102`, not `US-089`, because the backend keeps flood areas for only `FLOOD_EXTENT_KEEP_RUNS` runs.

**What a stored result changes**

Rana keeps results for one month ([[3di-simulation-orchestration]]), so a past run can be rebuilt from its `sim_id` without a new simulation.
That covers the single-timestep stages of `US-091` on the second replay's data, with `FLOOD_EXTENT_KEEP_RUNS` and `EDGE_TABLE_KEEP_RUNS` raised.
It does not cover `US-102` or the live sticky check.
The gate rejects a run older than 45 minutes (`MAX_NEWEST_AGE`), and a saved state older than a day cannot start a hotstart.
The four skipped slots never ran, so only a new simulation fills them.

**Two replay scopes**

| Scope | What it closes | Cost |
| ----- | -------------- | ---- |
| A. Full storm, about 13.5 hours (the subagent's plan) | `US-102`, the live sticky check and the single-timestep stages of `US-091`, and `US-089` | One full 3Di replay of about 52 runs |
| B. Rebuild plus a short slice (not verified) | `US-091` single-timestep stages from stored results, `US-089` now, and `US-102` on a slice of the storm that starts shortly before the gap | Fewer 3Di runs. The slice needs a design check, because the flood will be smaller and the ratio is judged on the mechanism, not the depth |

Recommendation: A unless the 3Di cost decides it, then a design check for B before planning.

**Steps to close each story (scope A)**

`US-102` (server and Mac)

1. Sunday, Mac: change `compose.yml` line 38 to `EDGE_TABLE_KEEP_RUNS: ${EDGE_TABLE_KEEP_RUNS:-60}`, commit, and the owner pushes.
   A hand edit of `compose.yml` on the server breaks the next pull.
2. Sunday, Mac: adapt `artifacts/docs/stories/evidence/us-063-replay-check.sh` into a read-only `US-102` check.
   It lists `flood_road_file` times against the slots, counts wet edges per table, and greps the Airflow logs for the Hotstart and Coldstart strings.
3. Monday 09:30, server, read-only: confirm the server checkout holds the standing-flood commit, no DAG import error exists, and `routing_adapter` is unpaused (the gate reads `flood_road_values`, which only `routing_adapter` writes).
4. Server, first change: fix `.env.rain-replay.json`.
   It holds the values from before the first replay: the 48-hour event of 2025-10-05 and a gate of 0.01.
   A `stop` would restore that old replay, not live rain.
   Back it up, then write empty `FLOOD_TEST_RAIN_CSV`, `FLOOD_TEST_RAIN_START`, and `FLOOD_TEST_RAIN_MM_HR`, and no gate line (`null`).
   Then run `git pull --ff-only alice modular`.
   Add to `.env` `FLOOD_EXTENT_KEEP_RUNS=100`, `EDGE_TABLE_KEEP_RUNS=100`, and `ARCHIVE_HOST_PATH=D:\airflow_new_data\archive` (create the folder first).
   Run `.\scripts\rain_env\replay.ps1 start -Event scripts\rain_events\hanoi_20260916_storm.csv -LeadMinutes 30 -Gate 5`.
   Do not run `stop` first. `start` overwrites the old replay, and the kept `.env.rain-replay.json` restores the live values later.
5. Unpause `flood_mapping_full` before the printed slot, with the owner's go.
6. Read the runs at hours 1, 3, 6.5, 8, and 13.
   The `BL-028` reading is about 18:30 +07, when the first table after the gap exists.
7. Tuesday 00:15: pause `flood_mapping_full`, run the `US-091` single-timestep step, copy the edge tables to `marie-curie/`, run the `US-102` check, then `stop` (see `US-089`).

`US-089`

1. Sunday, Mac: change the preview and status text to "at least N runs (gate only, `US-101` adds runs while the flood stands)", with a test.
   Add one line to `stop` so it expects mode `live` when the saved CSV is empty.
   The Mac has no `pwsh`, so the PowerShell edit is untested until the server.
2. Monday, server: run `start` twice inside one quarter-hour before unpausing, and compare `Get-FileHash .env`.
   That is the idempotency evidence.
3. Tuesday, after the pause and the table copy: run `replay.ps1 status`, then `replay.ps1 stop`.
   Copy tables and results first, because `stop` recreates the worker.
   The read-back must show `mode live`.

`US-091` (spike)

1. Sunday, Mac: fix the dependency to `US-102`, define the stages as the runs at event offset 0, 1h, and 3h, and state the live sticky method.
2. Live, at about +0:30, +1:30, and +3:30 after the start: turn the flag on for `floodmap-backend` only, run `experiment.py run --model sticky` on the newest table with `--departure-steps 2,3,4,5`, then turn the flag off.
   About 2 minutes per table.
3. After the pause, flag off: run `experiment.py run --model single_timestep` with the four table sets and departure steps 0 to 6, on 60 pairs (about 31 minutes).
   Save under `marie-curie/us-091/`.
4. Run the slow-travel case once on the 3h table, with `--slow-min-depth-cm` and `--slow-factor`.
5. Wednesday, Mac: write the summary tables, add the `D-nnn` decision to `decision-log.md`, and update the concept page.
   Report the 23 percent of requests with no route as dropped.

`US-094`

1. During step 4 of `US-102`: create `D:\airflow_new_data\archive`, set `ARCHIVE_HOST_PATH`, and recreate the worker.
   Read back with `docker exec airflow_new-airflow-worker-1 ls /opt/airflow/archive`.
   The replay's test-rain mode shows the `2b` skip, and `9_build_flood_tiles` still runs.
2. Measure the `results_3di.nc` sizes in the worker now, which replaces the 7 MB per run estimate.
3. The real-rain proof needs a forecast above 5 mm/h and cannot be scheduled, so it stays out of Sprint 13.

**Calendar (scope A)**

| When | What |
| ---- | ---- |
| Sat to Sun, 2026-10-10 to 10-11 | Mac changes, story text fixes, the owner pushes |
| Mon 10-12 | Planning, read-only server checks, pull, `.env`, `start` twice, replay starts about 10:45 +07, live sticky readings about 11:15, 12:15, 14:15, then every 3 hours |
| Tue 10-13 00:15 | Pause, single-timestep run, table copy, `US-102` check, `stop`, unpause for live rain |
| Wed 10-14 | `US-091` results and decision, evidence and details, resolve `BL-028` and perhaps `BL-026` |
| Thu to Fri 10-15 to 10-16 | Buffer for a failed replay, then refinement |

**Risks**

- The stop clause (five dry runs under 5 cm and no rain) is not exercised by a replay paused at hour 13.5.
  Say so in the details.
- A 3Di session limit (HTTP 429) hit once on 2026-10-01. The fallback is a retry on Wednesday night.
- `routing_adapter` could lag the gate by more than 45 minutes and end the chain. Check its runs at each reading.
- Disk: about 43 MB per run for `flood_extent_polygon`, so 100 runs is about 4.3 GB. Pause below 30 GiB free on C:.
- A live sticky run can find a crossing. That is the engine failing its own claim: log a blocker and keep the spike open.

**Blockers**

- [[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands|BL-028]] blocks the sprint goal. It moves to `resolved` when the five former-gap slots simulate, log Hotstart, and the first post-gap table is inside the ratio band.
- [[BL-023-9c-sampling-step-runs-over-770-seconds|BL-023]] was resolved by the product owner on 2026-10-10, so it is not a sprint blocker.
- [[BL-026-sticky-closure-clock-anchored-at-floored-departure|BL-026]] blocks reading the sticky result only.
  A crossing count of 0 on one route with a mid-step departure resolves it.

**Refinement before planning**

- `US-102`: rewrite the steps (no `stop`, 100 runs, the compose edit), the hotstart clause, the ratio, and the pause.
- `US-091`: fix the dependency, add the live-sticky method, the stage definitions, the dropped-route rule, and the decision.
- `US-094`: split it. Part one deploys the mount and shows the test-rain skip (S, ready, Sprint 13). Part two proves it on the first real run and measures growth (S, backlog). Remove the stale "Sprint 10" lines.
- `US-089` and `US-091` are carried work (`Reviewed` and `In progress`), not `Ready`. Say so at planning.
- Add a backlog story for a cap on standing-flood compute only if the replay shows the tail runs past 12 hours.

## Sprint backlog

```dataview
TABLE title AS "Story", kind AS "Kind", priority AS "Priority", estimate AS "Estimate", status AS "Status", epic AS "Epic"
FROM "docs/stories"
WHERE sprint = 13
SORT priority ASC, file.name ASC
```

## Review

Fill this on 2026-10-25.

## Retrospective

Fill this on 2026-10-25.

## Refinement for the next sprint

Fill this on 2026-10-25.

## Status history

- **2026-10-10, planning.** Created at the Scrum adoption ([[decision-log|D-024]]) so the first sprint has a home. Every story that was not `Done` returned to the backlog with `sprint` cleared. The old Sprint 13 to 16 placement of the frontend recheck ([[SP-04-frontend-recheck|sprint-plan-4]]) is dropped.
- **2026-10-10, planning.** The sprint length changed from one week to two weeks, and stories enter by story points and not by weeks ([[decision-log|D-026]]). The end date moved from 2026-10-18 to 2026-10-25. The picks stay unset until planning on 2026-10-12.
- **2026-10-10, planning.** The user chose replay scope A, the full storm, over the rebuild plus a short slice. Open decision 2 is now only the go.
- **2026-10-10, planning.** The owner asked to finish the replay stories during the weekend, so the replay moves from Monday 2026-10-12 to 2026-10-10 or 2026-10-11, and the Monday planning only confirms the picks. The server was checked read-only: it is 22 commits behind and can fast-forward, it contains the standing-flood commit, it has 100.9 GiB free on C:, `routing_adapter` is unpaused, and `flood_mapping_full` is paused. The server changes are waiting for the owner to allow them or run them.
- **2026-10-10, active.** The owner allowed the server writes. Done on the server: `.env.rain-replay.json` was fixed (backup `.bak-2026-10-10`), `git pull --ff-only alice modular` (after two clippings with a `?` in their names were renamed, because Windows rejects them), `.env` got `FLOOD_EXTENT_KEEP_RUNS=100`, `EDGE_TABLE_KEEP_RUNS=100`, and `ARCHIVE_HOST_PATH=D:/airflow_new_data/archive`, `replay.ps1 start` ran twice with an identical `.env` hash, and `flood_mapping_full` was unpaused at 04:02 +07. Slot 04:00 ran with a cold start, and `2b_archive_results` logged the test-rain skip.
- **2026-10-10, planning.** The replay finished at 18:49 +07. [[US-102-replay-the-storm-with-the-us-101-fix-to|US-102]], [[US-089-start-and-stop-a-rain-replay-on|US-089]], and [[US-091-measure-how-often-a-single-timestep-route|US-091]] are `Done`, and [[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands|BL-028]] and [[BL-026-sticky-closure-clock-anchored-at-floored-departure|BL-026]] are `resolved`. The proposed picks stay as they are, and open decisions 7 and 8 wait for the owner at planning.

