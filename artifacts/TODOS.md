# TODOS

## Current sprint: Sprints 9 to 12, 2026-10-05 to 2026-12-13

## Next action:
1. The second replay is over and `flood_mapping_full` is paused (since 01:29 +07 on 2026-10-10). The 48 depth tables are in `marie-curie/edge_tables_replay2_final_2026-10-10/`. The replay environment is still set, because `replay.ps1 stop` has not run. Decide between two ways to get the final `US-092` and `US-093` runs. (a) Run them now on these tables with `marie-curie/run_option_a_real.py` (30 pairs, steps 0 and 4, budget 3,000,000, seed 1, 5 workers, about 25 minutes), and name the one-hour gap and the cold start at 20:30 +07 in the result. (b) Replay the storm with the `US-101` fix first (about 12 hours), then run them on tables with no gap. A first run on the 30 tables up to 21:15 +07 is recorded in `US-093`.
2. **P0, `BL-028` (`monitoring`):** the `US-101` fix (the 5 mm/h gate only from a dry state, then simulate until the newest 5 runs of `flood_road_values` are under 5 cm and no rain is forecast) is on the server at `9090cbe`, and its tests pass there. It has not run in a replay. To close the blocker, run `replay.ps1 stop`, start the storm replay again, unpause `flood_mapping_full`, and check that no slot is skipped and the run after a quiet stretch hotstarts. Say go when you want it.
3. `US-070` and `US-086` are done (2026-10-10). Decide what to do about the growth of `9c` within a chain (`BL-023`, 46 s to 96 s, cause unknown), or leave it at `monitoring`.
4. `US-094` waits for a real Tomorrow.io forecast above 5 mm/h. The archive mount of `US-094` in `compose.yml` needs the Airflow containers recreated on the server, which has not been done. No copy of the per-timestep values is kept until `US-094` runs on real rain (D-022).
5. Decide whether `TIME_AWARE_ROUTING` goes on for good (`rollout.ps1 -LeaveOn` and `TIME_AWARE_ROUTING=true` in `.env`), best with the DAG running on real rain. The flag is off now.
6. `BL-027`: you set the exact-enough bar at 97 percent per vehicle (2026-10-10). The storm run (30 tables) meets it for every vehicle (lowest 0.987). Still open: the cost limit and pair count (proposal: 30 pairs, 2 hours, the final run takes about 40 minutes). The blocker resolves when the final run on the 45 tables confirms 97 percent per vehicle.

Done on 2026-10-10 and removed from this list: `US-069` (storage check, passes), `US-095` (netcdf ingest retired and tables dropped), `US-101` (rain gate fix), and `US-097` and `US-099` from 2026-10-09. `US-100`, `US-070`, and `US-086` are `Done` (2026-10-10) and leave at the next rollover. Done on 2026-10-09 and removed earlier: the `graphhopper` rollout for `US-096` and `US-097`, the format-2 graph export (blocker [[BL-024-edge-export-has-no-node-ids|edge-export-has-no-node-ids]] `resolved`), and the test for a via request with a shallow road. Records are in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]], the epic files, and the logs of [[2026-10-09]] and [[2026-10-10]].

### Done - US-070 Stop a slow sampling step from holding the database

**Result (2026-10-10):** the cancel at 120 s is in place and no run of 92 reached it (longest 96 s). `BL-023` stays `monitoring`: `9c` still rises within a chain (46 s to 96 s), cause unknown. Evidence: `us-070-9c-in-airflow-check-output.png`.

**What:** Task `9c` ran over 770 s in one sampling step during the replay. It now analyzes `flood_depth_raster_tile` first and cancels a step past 120 s ([[EP-08-edge-depth-table|edge-depth-table-stories]] Story E8).

**Effort:** S
**Priority:** P1
**Depends on:** `US-041`, done.

**Sprint:** 10, [[EP-08-edge-depth-table|edge-depth-table-stories]] Story E8 (US-070), in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]].

**Blocker tracking:** [[BL-023-9c-sampling-step-runs-over-770-seconds|9c-sampling-step-runs-over-770-seconds]].

**Status note:** built and pushed as `5e358bf`, 133 tests pass. The server is at `4d262ef`, which contains it. Run `20261006T104500` took 51.1 s and its `ANALYZE` ran. The blocker closes after several more 9c runs under load stay near 50 s. The 12-hour replay that started on 2026-10-08 supplies those runs.

**2026-10-08 readings:** over 9 runs `9c` took 46 to 64 s (63.1 s at most), and no step passed the 120 s cancel. The blocker closes when `9c` stays near 50 s, and it rose by about 2 s per run, so the item stays open until the numbers level off after 03:00 +07 on 2026-10-09.

**2026-10-09 readings (45 runs):** `9c` took 44.8 to 90.3 s, and no step passed the 120 s cancel. The first chain rose from 44.8 to 90.3 s over 27 runs. The chain restarted at 22:49 +07 and the second chain went from 45.7 to 62.1 s, then held at 60.4 to 62.1 s for its last 6 runs. The time does not level off near 50 s, so the story stays `Reviewed` and the blocker stays `monitoring`. The growth resets at a chain restart, which points at rows that `flood_road_values` accumulated. The first prune of `US-086` ran on 2026-10-09 (14.8 million rows down to 1.1 million). Read the `9c` durations of the next `routing_adapter` runs: if the growth within a chain stops, close the blocker.

### Active - US-094 Archive `results_3di.nc` and a run record to D: when the pipeline reads real rain

**What:** A new task after `2_download_results` copies `RESULT_DIR/<sim_id>/results_3di.nc` and a run record (`sim_id`, rain input, model revision, graph hash, run timestamp) to an archive folder on D:. It skips when `FLOOD_TEST_RAIN_CSV` or `FLOOD_TEST_RAIN_MM_HR` is set. `9_build_flood_tiles` waits for it, so the 24-hour cleanup cannot delete the file first. The task logs the free space of D: after each copy and fails loudly below a floor (proposed 50 GB, to confirm with you). The daily growth in GB is measured ([[EP-15-archive-and-netcdf-retirement|US-094-095-archive-and-netcdf-retirement-stories]] Story 1, D-016).

**Effort:** M
**Priority:** P1
**Depends on:** none to build. A one-off run with the real Tomorrow.io forecast counts as the proof (your decision of 2026-10-08), and it waits for a real forecast above the rain gate (5 mm/h), with no gate change and no override (your choice of 2026-10-08). `US-095` and `US-086` wait for it. The folder is `D:\airflow_new_data\archive`, confirmed by you on 2026-10-08.

**Sprint:** 10, [[EP-15-archive-and-netcdf-retirement|US-094-095-archive-and-netcdf-retirement-stories]] Story 1 (US-094), in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]].

**Status note:** `Reviewed`. Built on `modular` (not pushed, not deployed): `scripts/archive_results.py`, task `2b_archive_results`, a join task `2c_archive_done` so a full drive does not stop the tile build, and the `ARCHIVE_HOST_PATH` mount. 24 tests pass. The deploy waits for the end of the second replay, and the proof waits for a real forecast above 5 mm/h. It blocks `US-095`.

### Done - US-086 Prune old rows of `flood_road_values`

**Result (2026-10-10):** the prune task ran 45 times inside Airflow, and the table holds 55 runs, exactly 24 hours (830 MB, 1,319,880 rows). Evidence: `us-086-prune-in-airflow-check-output.png`.

**What:** Rows older than 24 hours leave the table (D-017), measured from the newest run in the table. The task goes in `routing_adapter` after `flood_on_roads`, with the window in a new variable. The size is read first and recorded in [[core-output-contract]] (6,955 MB on 2026-10-08, about 18 MB per run).

**Effort:** S
**Priority:** P2
**Depends on:** `US-073` (`Done`). The `US-094` gate of D-017 was waived by you on 2026-10-09 (D-019).

**Sprint:** 12, [[EP-12-core-output-hygiene|core-output-hygiene-stories]] Story 1 (US-086), in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]].

**Status note:** `Reviewed`. Built, merged on `modular` (`4f6569d`), and the first prune ran on 2026-10-09 at your go: 368 runs and 13,749,316 rows deleted in about 40 s, 45 runs (1,087,512 rows) kept, then `VACUUM (ANALYZE)`. Evidence is in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]. It reaches `Done` after the task `prune_flood_road_values` runs once inside Airflow, which needs the next replay. `VACUUM (FULL, ANALYZE)` ran at your go (7.4 s): the table went from 7,497 MB to 537 MB with the 7 indexes, rows intact (1,087,512), and `minio_custom` from 9,290 MB to 2,330 MB. C: free stayed at 104.4 GiB, because `docker_data.vhdx` does not shrink by itself. Its effect on `9c` decides `US-070`.

### Active - US-089 Start and stop a rain replay on the server with one command each

**What:** `replay.ps1` starts, stops, and reports a replay, idempotently, and reads the values back inside the worker.

**Effort:** M
**Priority:** P1
**Depends on:** None to build.

**Sprint:** 12, [[EP-13-rain-replay-test-environment|rain-replay-test-environment-stories]] Story 2 (US-089), in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]].

**Status note:** `Reviewed`. `start` ran on 2026-10-08. It stays open until the second replay runs after Sprint 12 and `stop` runs (D-020), then needs a screenshot.

### Active - US-091 Measure how often a single-timestep route meets a closed road on arrival

**What:** The harness (pair sampler, route call, re-walk, result writer) and the violation rate by vehicle, length class, departure step, and storm stage.

**Effort:** M
**Priority:** P1
**Depends on:** `US-047`, `US-050`, `US-052`, and `US-055` (all `Done`), and the depth tables of a replay. Only 3 tables of the 12-hour replay remain (copied to `marie-curie/edge_tables_replay_2026-10-09/`).

**Sprint:** 12, [[EP-14-routing-paper-experiments|US-090-093-routing-paper-experiments-stories]] Story 2 (US-091), in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]].

**Status note:** `In progress`. The harness is built and merged on `modular` (`04c0288` to `245b90d`, package `scripts/routing_experiments/`, 41 tests pass, the server run is not done). The storm stages need the second replay, which runs after Sprint 12 (D-020), so this row cannot reach `Done` inside Sprint 12. Three things to know. First, the runner walks engine routes from the time of the request since `US-096` (`88c151c`). Second, the sticky engine cannot be checked on the old replay tables, because the backend departs at the later of the step time and now, so the sticky check needs live tables. Third, the single-timestep plan reads database flood areas and the re-walk reads the edge depth table of the same run, two depth sources, and the result file must say so.

### Active - US-092 Test how the vehicle limits change the result

**What:** The same experiment with the vehicle limits varied.

**Effort:** M
**Priority:** P2
**Depends on:** `US-091` (its harness and pair set). Moves to Sprint 13 if the harness slips.

**Sprint:** 12, [[EP-14-routing-paper-experiments|US-090-093-routing-paper-experiments-stories]] Story 3 (US-092), in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]].

**Blocker tracking:** [[BL-024-edge-export-has-no-node-ids|edge-export-has-no-node-ids]]. [[BL-025-engine-has-no-depth-band-cost|engine-has-no-depth-band-cost]] is `resolved` by D-021.

**Status note:** `In progress`. The limit sweep is built and merged on `modular` (`bb00594`, `scripts/routing_experiments/limit_sweep.py`, 12 tests): closed length, route share, mean detour, violation rate, a regret table (plan limit A, judge limit B), and a list of settings where the conclusion changes. It runs on the Python reference with a synthetic graph. The cost band is replaced by the precaution fraction (D-021), swept at 0.25, 0.5, and 0.75 by `sweep_fraction` in `precaution.py` (merged, `044adfe`). The real-graph runner `scripts/routing_experiments/real_run.py` ran on the 3 dry tables of the first replay (`marie-curie/real_run_replay1_seed1.json`). A preliminary run on the storm tables of the second replay ran from 21:55 to 22:17 +07 (30 tables, 30 pairs, steps 0 and 4, seed 1, 5 workers, 60 settings, output `marie-curie/real_run_replay2_prelim_seed1.json`, graph hash `8c13d884`). The runner works at storm scale. The result file's comparison baseline is the first setting (13:00, step 0, before the rain), so its list of 58 settings that differ from the baseline does not answer the story yet. Read the regret table and the fraction sweep from the final run. The final run on the full table set waits for 00:45 +07 on 2026-10-10 (next action 1), so the story stays `In progress`.

### Active - US-093 Measure how often the sticky rule gives no route or a longer route than an arrival-only reference

**What:** The share of routes with no route or a detour against an arrival-only reference.

**Effort:** S
**Priority:** P2
**Depends on:** `US-047`, `US-050` (both `Done`), the depth tables of a replay, and the sampler of `US-091`.

**Sprint:** 12, [[EP-14-routing-paper-experiments|US-090-093-routing-paper-experiments-stories]] Story 4 (US-093), in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]].

**Blocker tracking:** [[BL-024-edge-export-has-no-node-ids|edge-export-has-no-node-ids]].

**Status note:** `In progress`. The arrival-only search (`scripts/routing_reference/arrival_only.py`, label-correcting, `exact` flag) and the per-pair comparison with sticky closure (`scripts/routing_experiments/sticky_cost.py`) are merged on `modular` (`fc14d81` to `ae824ea`, 24 tests, a seeded 300-graph property test shows sticky never ends earlier than arrival-only). The estimate stays S. A first storm-wide run (7,200 searches, 30 tables up to 21:15 +07) is recorded in the story. The final run waits for the end of the second replay (D-020), see next action 1.

### Done - US-100 Decide between option A closure and sticky closure for a vehicle already on the route

**What:** Read what each closure rule means for a vehicle already on the route, then record the chosen rule. On the grid, sticky closure has no route in 128 cases where option A has one and arrives later in 64. If option A can send a vehicle into a segment that floods while it is still in it, sticky closure is the safer default ([[EP-14-routing-paper-experiments|US-090-093-routing-paper-experiments-stories]] Story 6).

**Effort:** XS
**Priority:** P2
**Depends on:** `US-099` for the decision. The reading of the two rules can start now.

**Sprint:** 12, [[EP-14-routing-paper-experiments|US-090-093-routing-paper-experiments-stories]] Story 6 (US-100), in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]].

**Blocker tracking:** [[BL-027-arrival-only-reference-is-inexact-on-the-real-graph]].

**Result (2026-10-10):** you decided to keep sticky closure ([[decision-log|D-023]]). Evidence: `us-100-closure-reading-output.png`. No code changes.

## Backlog

No unfinished item from Sprint 8 is left. The Done items of Sprints 9 to 11 (`US-051` to `US-054`, `US-071`, `US-072`, `US-074`, `US-075` on 2026-10-08, and `US-045`, `US-055`, `US-073`, `US-088`, `US-087`, `US-090`, `US-096`, `US-097`, `US-099` on 2026-10-09, and `US-069`, `US-095`, `US-101` on 2026-10-10) were deleted. Their records are in the epic files and in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]].

## Blockers for the next sprint

The next sprint is Sprint 13, planned for 2026-12-14 to 2026-12-20 in [[SP-04-frontend-recheck|sprint-plan-4]]. Its rows enter this file when the sprint starts, not before (rule 9).

Any blocker stops Sprint 13: None known. Sprint 13 is the frontend recheck, which reads no open blocker below except [[BL-018-route-panel-stuck-on-loading-bars|route-panel-stuck-on-loading-bars]] and [[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]], both monitoring.

The unresolved blockers are:

1. [[BL-018-route-panel-stuck-on-loading-bars|route-panel-stuck-on-loading-bars]], monitoring.
2. [[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]], monitoring.
3. [[BL-011-routing-not-time-aware|routing-not-time-aware]], which `US-055` resolves.
4. [[BL-023-9c-sampling-step-runs-over-770-seconds|9c-sampling-step-runs-over-770-seconds]], monitoring, fixed in code by `US-070`. It blocks no build.
5. [[BL-021-place-name-slow-after-map-tap|place-name-slow-after-map-tap]], which blocks no build. Its story `US-061` has no sprint.
6. [[BL-026-sticky-closure-clock-anchored-at-floored-departure|sticky-closure-clock-anchored-at-floored-departure]], monitoring, fixed in code by `US-096`. It resolves after the next rollout rebuilds the `graphhopper` image. It blocks no build.
7. [[BL-025-engine-has-no-depth-band-cost|engine-has-no-depth-band-cost]], `resolved` by D-021 on 2026-10-09.
8. [[BL-024-edge-export-has-no-node-ids|edge-export-has-no-node-ids]], `resolved` on 2026-10-09. The second replay is over, and the real-graph run of `US-092` and `US-093` waits for your choice in next action 1.
9. [[BL-027-arrival-only-reference-is-inexact-on-the-real-graph]], open. It blocks only `US-093` and blocks no build in Sprint 13. The fix waits for your decision on the definition of the reference.
10. [[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands|rain-gate-stops-simulation-while-the-flood-still-stands]], P0, monitoring, fixed in code by `US-101` and deployed on the server. It resolves after a replay of the storm with the fix. It blocks no build in Sprint 13.
