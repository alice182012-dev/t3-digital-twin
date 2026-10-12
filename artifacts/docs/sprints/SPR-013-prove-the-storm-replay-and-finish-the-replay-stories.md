---
date: 2026-10-10
type: sprint
sprint_id: "SPR-013"
sprint: 13
start_date: 2026-10-12
end_date: 2026-10-25
status: active
tags: [sprint]
related: ["[[scrum-framework]]", "[[Velocity]]", "[[decision-log|D-024]]", "[[decision-log|D-033]]", "[[decision-log|D-034]]"]
---

# SPR-013 Sprint 13: EP-21 foundation

The first sprint under Scrum ([[decision-log|D-024]]). It runs two weeks, from Monday 2026-10-12 to Sunday 2026-10-25 ([[decision-log|D-026]]). Planning was on 2026-10-12, and the product owner confirmed the goal and the picks that day. [[TODOS]] shows the sprint in the terminal.

## Sprint goal

EP-21 foundation: the industry apps can read flood history and run analysis in their own container.

Confirmed by the product owner on 2026-10-12. The sprint is backend only, with no frontend story.

## Planning

- **Velocity.** The last three sprints gave 7, 15, and 25 points ([[Velocity]]). Those sprints lasted days, not two weeks, so they under-measure a two-week sprint. The product owner set the forecast at 16 points on 2026-10-12.
- **Picks.** Six stories make 15 points, one under the forecast of 16. Each one passes the INVEST check in [[scrum-framework]]. The table lists them in the order to start them.

| Order | Story | Title | Estimate | Points | Depends on |
| ----- | ----- | ----- | -------- | ------ | ---------- |
| 1 | [[US-115-decide-whether-the-edge-depth-table-replaces-flood-road-values\|US-115]] | Decide whether the edge depth table replaces flood_road_values (spike) | M | 3 | none |
| 2 | [[US-094-archive-results-3di-nc-and-a-run\|US-094]] | Deploy the archive mount and show the test-rain skip (part one) | S | 2 | none |
| 3 | [[US-106-keep-per-segment-depth-history-in-timescaledb\|US-106]] | Write per-segment depth history to TimescaleDB (part a) | M | 3 | [[US-105-decide-what-flood-history-the-industry-apps-need\|US-105]], Done |
| 4 | [[US-109-run-an-analysis-service-in-its-own-container\|US-109]] | Run an analysis service in its own container | M | 3 | [[US-107-create-a-read-only-role-for-any-consumer-app\|US-107]] and [[US-108-publish-a-run-manifest-for-the-core-outputs\|US-108]], Done |
| 5 | [[US-112-keep-the-edge-depth-files-to-the-contract-count\|US-112]] | Keep the edge depth files to the newest 8 runs | S | 2 | none |
| 6 | [[US-104-compare-the-two-inputs-of-the-flood-tile-build\|US-104]] | Compare the two inputs of the flood tile build (spike) | S | 2 | [[US-103-move-the-flood-tile-build-into-its-own-dag\|US-103]], Done |
| | | Total | | 15 | |

- **Order of work.** [[US-115-decide-whether-the-edge-depth-table-replaces-flood-road-values|US-115]] starts first, as the product owner asked, with [[US-094-archive-results-3di-nc-and-a-run|US-094]] in the second slot. [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]] starts after the spike decides, because the answer may change what it builds.
- **Work in progress.** At most two stories are `In progress` at once. No story was set to `In progress` at planning.
- **Not picked.** [[US-113-backfill-per-segment-depth-history|US-113]] and [[US-110-decide-whether-pipeline-tables-leave-the-public-schema|US-110]] left the sprint on 2026-10-12 to make room for the spike, and [[US-116-let-a-run-with-no-wet-road-piece-win-the-winner-query|US-116]] waits in the backlog for its decision. [[US-102-replay-the-storm-with-the-us-101-fix-to|US-102]], [[US-089-start-and-stop-a-rain-replay-on|US-089]], and [[US-091-measure-how-often-a-single-timestep-route|US-091]] are `Done` and keep an empty `sprint`, because the product owner has not decided to count them. [[US-114-prove-the-real-rain-archive-and-measure-growth|US-114]] is not in this sprint and has no sprint, because its proof waits for a real forecast above 5 mm/h. The owner said on 2026-10-12 that no rain is expected, so the story stays in the backlog in monitoring ([[decision-log|D-037]]).

**Open decisions for the product owner:** none on 2026-10-12.

**Resolved on 2026-10-12:**

- The 50 GB free-space floor for the archive (`ARCHIVE_MIN_FREE_GB`) is confirmed. It is for [[US-114-prove-the-real-rain-archive-and-measure-growth|US-114]], not for a pick in this sprint ([[decision-log|D-037]]).
- ~~A lowered rain gate may prove the archive in [[US-114-prove-the-real-rain-archive-and-measure-growth|US-114]] if no forecast passes 5 mm/h by 2026-10-23. The value of the lowered gate is not set ([[decision-log|D-035]]).~~ Withdrawn the same day. The rain gate stays at 5 mm/h, and no lowered gate is set ([[decision-log|D-037]]).
- A run that wets no road piece is recorded as dry, at depth 0 cm. This settles the open question of [[US-113-backfill-per-segment-depth-history|US-113]] ([[decision-log|D-036]]).
- `TIME_AWARE_ROUTING` stays on. The product owner gave the go on 2026-10-12, and the server reads `true` for `floodmap-backend` as of that day's read-back ([[decision-log|D-034]]).
- The edge depth files keep the newest 8 runs ([[decision-log|D-033]]).

**Removed:** the replay questions (the go, the pause time, the hotstart clause, the pair count, and the question of [[BL-023-9c-sampling-step-runs-over-770-seconds|BL-023]]). The replay or the product owner answered each one on 2026-10-10, and the stories that held them are `Done`.

## Replay plan of 2026-10-10 (done)

The replay ran on 2026-10-10, and its results are in [[US-102-replay-the-storm-with-the-us-101-fix-to|US-102]], [[US-089-start-and-stop-a-rain-replay-on|US-089]], and [[US-091-measure-how-often-a-single-timestep-route|US-091]].
The text below is the plan as it was analysed on 2026-10-10, kept as the record.

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

No open blocker blocks the Sprint 13 goal.

- [[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands|BL-028]] and [[BL-026-sticky-closure-clock-anchored-at-floored-departure|BL-026]] are `resolved` (2026-10-10).
- [[BL-023-9c-sampling-step-runs-over-770-seconds|BL-023]] was resolved by the product owner on 2026-10-10.

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
- **2026-10-12, active.** The product owner confirmed the goal and set the forecast at 16 points. Seven stories are picked, with `sprint: 13`, and [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]] is split into part (a), which is picked, and [[US-113-backfill-per-segment-depth-history|US-113]], which is picked too. [[US-094-archive-results-3di-nc-and-a-run|US-094]] is split into part one, which is picked, and [[US-114-prove-the-real-rain-archive-and-measure-growth|US-114]], which is in the backlog. [[decision-log|D-033]] set the edge depth count to 8 for [[US-112-keep-the-edge-depth-files-to-the-contract-count|US-112]], and [[decision-log|D-034]] kept `TIME_AWARE_ROUTING` on. The server was not touched. Later that day, the product owner resolved the 50 GB floor and the lowered rain gate ([[decision-log|D-035]]), and the question of a run that wets no road piece ([[decision-log|D-036]]). The product owner also gave the go on the server change for `TIME_AWARE_ROUTING` ([[decision-log|D-034]]). [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]] checks compression by hand on one chunk, as its acceptance check now says.
- **2026-10-12, active.** The product owner withdrew the lowered rain gate that [[decision-log|D-035]] had allowed, the same day ([[decision-log|D-037]]). The owner said that no rain is expected. The rain gate stays at 5 mm/h, and the 2026-10-23 cutoff is removed. [[US-114-prove-the-real-rain-archive-and-measure-growth|US-114]] stays in the backlog with no sprint and is not in Sprint 13. The 50 GB floor stands.
- **2026-10-12, active.** The product owner asked for the question "what does routing do with a run that wets no road piece" to be worked first, and left the form to the team. It is one spike, [[US-115-decide-whether-the-edge-depth-table-replaces-flood-road-values|US-115]] (M, 3 points, P0), because the fix of [[US-116-let-a-run-with-no-wet-road-piece-win-the-winner-query|US-116]] depends on its answer. Adding it took the sprint to 19 points, so [[US-113-backfill-per-segment-depth-history|US-113]] (blocked by the answer through US-106) and [[US-110-decide-whether-pipeline-tables-leave-the-public-schema|US-110]] (P3) left, and the sprint holds 15 points. The product owner can swap another story out.
- **2026-10-12, active.** Four of the six picks are `Done` (10 of 15 points): [[US-115-decide-whether-the-edge-depth-table-replaces-flood-road-values|US-115]], [[US-094-archive-results-3di-nc-and-a-run|US-094]], [[US-109-run-an-analysis-service-in-its-own-container|US-109]], and [[US-112-keep-the-edge-depth-files-to-the-contract-count|US-112]]. [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]] is `Reviewed` and waits for one event-triggered run, a server screenshot, and the owner's acceptance. [[US-104-compare-the-two-inputs-of-the-flood-tile-build|US-104]] is not started. The spike decided [[decision-log|D-038]] (replace `flood_road_values` in stages, accepted by the product owner), and [[US-116-let-a-run-with-no-wet-road-piece-win-the-winner-query|US-116]] was done the same day outside the sprint plan because it fixes a live bug and the decision needed it. The stories of the staged replacement, [[US-117-export-a-stable-key-with-each-graph-edge|US-117]] to [[US-123-delete-flood-on-roads-and-flood-road-values|US-123]], and the test dataset ([[decision-log|D-039]], [[EP-22-keep-a-real-storm-as-the-test-dataset|EP-22]], [[US-124-save-the-storm-replay-results-and-derived-data|US-124]] to [[US-128-run-the-test-suites-against-the-test-databases|US-128]]) are in the backlog and do not change the sprint goal.

