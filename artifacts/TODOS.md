# TODOS

## Current sprint: Sprints 9 to 12, 2026-10-05 to 2026-12-13

## Next action:
1. The second replay is running (started on 2026-10-09 at your go, D-020). `EDGE_TABLE_KEEP_RUNS` is 60 in the server's `compose.yml` (a local edit there, not committed) and in the worker. Chain 1 runs 13:30 to 19:15 +07 on 2026-10-09 (24 runs), chain 2 runs 20:30 to 00:45 +07 on 2026-10-10 (18 runs). The hour-6 reading for `US-069` was taken at 19:30 +07 (log of 2026-10-09). After 00:45 +07, in this order: (a) the hour-12 reading for `US-069` was taken at 00:59 +07 on 2026-10-10 and passes (see the item and [[2026-10-10]]); (b) done on 2026-10-10: the 48 tables are in `marie-curie/edge_tables_replay2_final_2026-10-10/` and the 4 missing tables are the 4 runs the gate skipped, which is the P0 blocker [[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands|BL-028]] (see [[2026-10-10]]); (c) rerun the `US-093` sample on all the tables with `marie-curie/run_option_a_real.py` (30 pairs, steps 0 and 4, budget 3,000,000, seed 1, 5 workers, about 25 minutes), which now also records the extra time of each `sticky_longer` case; (d) only then run `replay.ps1 stop` (the DAG was paused at 01:29 +07 on 2026-10-10, before (c), because the tables are copied and nothing on the server is needed). A first run on the 30 tables up to 21:15 +07 is recorded in `US-093`. This unblocks the storm stages of `US-091`, `US-092`, and `US-093`.
2. While the replay runs, build on the Mac only (no pull, build, or `compose.yml` commit on the server until the replay ends, because the DAG files are bind-mounted). First, a runner for `US-092` and `US-093` that loads the real graph and the depth tables, samples node pairs, runs `sweep_fraction`, `compare`, and the limit sweep, and writes a result file with the one-way and speed limits. Test it on the 3 tables in `marie-curie/edge_tables_replay_2026-10-09/`. Second, `US-094` (the archive task, unit-tested locally). `US-098` is not scheduled. Then run the real-graph sweeps of `US-092` and `US-093` on the tables of that replay. The loader is `scripts/routing_experiments/real_graph.py`. The result file must say that one-way roads are open both ways and that travel time is length at 30 km/h. On 2026-10-09 at 21:55 +07 two Mac-only jobs started: the preliminary real-graph run of `US-092` on the storm tables of the second replay (item 1 repeats it on the full set), and the code removal of `US-095` on a local branch.
3. Read the `9c` durations of the next `routing_adapter` runs (`US-070`). The task `prune_flood_road_values` also runs inside Airflow for the first time, which moves `US-086` to `Done`.
4. `US-094` waits for a real Tomorrow.io forecast above 5 mm/h. `US-095` and the netcdf drop are done (2026-10-10, D-022), so no copy of the per-timestep values is kept until `US-094` runs on real rain.
5. `US-069` is closed: both readings were taken on time in the second replay and pass (hour 12 on 2026-10-10 at 00:59 +07). The story is `Done` (2026-10-10).
6. Decide whether `TIME_AWARE_ROUTING` goes on for good (`rollout.ps1 -LeaveOn` and `TIME_AWARE_ROUTING=true` in `.env`), best with the DAG running on real rain. The flag is off now.
7. Decide between option A and sticky closure (`US-100`). You chose option A as the reference on 2026-10-09 (`BL-027`). The pruned search is exact for 0.993 of 7,200 searches on the storm tables up to 21:15 +07, and every inexact search has a proven bound. `US-100` still needs your call on what each closure rule means for a vehicle already on the route, and `BL-027` needs your answer on the exact-enough bar.
8. **P0, `US-101` (`Done`, `BL-028` `monitoring`):** the rain gate stopped the simulation while the flood stood ([[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands|BL-028]]). The fix is committed locally as `5f115f4` and not on the server. `flood_mapping_full` was paused at 01:29 +07 on 2026-10-10. Decide when to pull it and replay the storm with it. The final runs of `US-092` and `US-093` (item 1 (c)) wait for that replay.

Done on 2026-10-09 and removed from this list: the `graphhopper` rollout for `US-096` and `US-097`, the format-2 graph export (copied to `D:/airflow_new_data/data/mapping/graph_export`, blocker [[BL-024-edge-export-has-no-node-ids|edge-export-has-no-node-ids]] `resolved`), and the test for a via request with a shallow road (`f555e71`, run 37889625407). Records are in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]] and the log of 2026-10-09.

### Done - US-101 Keep simulating while the flood still stands after the rain stops

**Result (2026-10-10):** the rain gate now applies only from a dry state, and the simulation runs until the newest 5 runs of `flood_road_values` are under 5 cm and no rain is forecast. Committed as `5f115f4`, 12 unit tests and 3 gate tests pass. Evidence: `us-101-gate-check-output.png`. The replay on the server has not run, so `BL-028` stays `monitoring`.

**What:** `flood_mapping_full` skips every run whose forecast rain is under 5 mm/h, even while the roads still hold water, and the first run after the skips starts cold from a dry model. Make the DAG keep simulating and publishing depths until the roads are dry, and hotstart after a quiet stretch ([[EP-12-core-output-hygiene|core-output-hygiene-stories]] Story 3).

**Effort:** M
**Priority:** P0
**Depends on:** nothing open. You chose the rule on 2026-10-10.

**Sprint:** 12, [[EP-12-core-output-hygiene|core-output-hygiene-stories]] Story 3 (US-101), in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]].

**Blocker tracking:** [[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands|rain-gate-stops-simulation-while-the-flood-still-stands]].

**Status note:** `Done`. Built on `modular` (`scripts/standing_flood.py`, the gate in `dags/flood_mapping_dag.py`), 12 unit tests and 3 gate tests pass, committed as `5f115f4`, not pushed and not on the server. The rule: the 5 mm/h gate applies only from a dry state, and the simulation then runs until the newest 5 runs of `flood_road_values` are under 5 cm and the forecast rain is 0. Next: pull on the server and replay the storm with the fix. Concerns are in the blocker. The fault, in the second replay: 4 runs (19:30 to 20:15 +07, forecast 3.57 to 4.52 mm/h) were skipped, no tables exist for them, and the run at 20:30 +07 started cold ("No saved state within 0:30:00"). For the same clock time (13:45 Z) the table before the gap forecast 3,939 wet edges and 1,614 at 20 cm or more, and the table after it shows 1,185 and 254. The final runs of `US-092` and `US-093` wait for this story.

### Active - US-070 Stop a slow sampling step from holding the database

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

### Done - US-095 Retire the `netcdf_values` ingest

**Result (2026-10-10):** deployed and dropped on the server. `flood_metrics` went from 5,395 MB to 9,942 kB, the three `storage-postgres` netcdf tables are gone, and the DAG has no task `3b`. C: free is unchanged because `docker_data.vhdx` does not shrink. Evidence: `us-095-drop-check-output.png`. [[decision-log|D-022]] records that you waived the wait for `US-094`.

**What:** Remove task `3b_upload_netcdf_postgres`, the tables `netcdf_values`, `mesh_elements`, and `netcdf_variable_catalog`, the two `storage-postgres` tables `netcdf_files` and `netcdf_variables`, and the scripts and tests that use them. `0b_ensure_schema` still creates the three empty tables. The server drop runs in order (`netcdf_values`, then the catalog) and records the `timescaledb` size and the C: free space ([[EP-15-archive-and-netcdf-retirement|US-094-095-archive-and-netcdf-retirement-stories]] Story 2, D-018).

**Effort:** M
**Priority:** P1
**Depends on:** `US-094` proven on real rain. The server drop needs your explicit go.

**Sprint:** 11, [[EP-15-archive-and-netcdf-retirement|US-094-095-archive-and-netcdf-retirement-stories]] Story 2 (US-095), in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]].

**Status note:** `In progress`. The code is built and committed on the local branch `us-095-retire-netcdf-ingest` (`9b79b0d`, from `modular`, not pushed, not deployed). Task `3b_upload_netcdf_postgres`, its three loader scripts, and `create_netcdf_tables.py` are gone, and `0b_ensure_schema` still creates the three empty tables. The DAG graph tests pass (82 pass and 10 fail in `test/`, the same 10 as on `modular`, all in `threedi_api_client` tests). Nothing touches the server until someone pulls there after the second replay. The server drop still waits for `US-094` proven on real rain and for your explicit go. One thing to decide before the drop: `create_netcdf_tables.py` also created a `netcdf_values` table on `storage-postgres`, with a foreign key to `netcdf_files`, and the story names only `netcdf_files` and `netcdf_variables` for that database. Dropping `netcdf_files` fails until that table goes first. A read-only check at 22:10 +07 found it empty (0 rows, 56 kB), `netcdf_files` at 316 rows (752 kB), `netcdf_variables` at 9,361 rows (3.7 MB), no view or function that uses them, and foreign keys only between these three. Drop order is `netcdf_values`, `netcdf_variables`, `netcdf_files`, and only after the branch is deployed, because the running DAG code recreates the tables and `3b` fails on a missing one. Details are in the story.

### Active - US-086 Prune old rows of `flood_road_values`

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

### Done - US-097 Recommend a route that avoids the precaution depth, and keep the hard-limit route as a second option

**Result:** the server rollout rebuilt the images from `modular` (`11f6373`), every script check passed, and `POST /route` for a trip with a shallow road returned two paths with `td.kinds: "recommended,through_water"`. Evidence: `us-097-through-water-route-output.png`.

**What:** The engine plans with the hard limit first, and with 50 percent of it only when the first route touches a road at that depth. `POST /route` returns the recommended route and the through-water option ([[EP-16-precaution-depth-routing|US-097-098-precaution-depth-routing-stories]] Story 1, D-021).

**Effort:** M
**Priority:** P1
**Depends on:** `US-096` (`Done` in code), the fraction sweep of `US-092`, and your go on the response contract.

**Sprint:** 12, [[EP-16-precaution-depth-routing|US-097-098-precaution-depth-routing-stories]] Story 1 (US-097), in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]].

**Status note:** `Done`. Built and merged on `modular` (`11f6373`, the combined state ran on branch `ci-modular-combined`: 137 Java tests passed on GitHub Actions, run 37885851481, and 31 backend tests pass). The Python reference is `scripts/routing_experiments/precaution.py`. The contract: `POST /route` returns path 0 as the recommended route and path 1 as the through-water route. The hints are `td.kinds` (`recommended`, `recommended,through_water`, or `through_water`), `td.limit_cm`, and `td.precaution_cm`. The fraction is the profile hint `td_precaution_fraction` (default 0.5). The hard-limit search runs first and the second search runs only when that route touches the precaution depth. The `graphhopper` image was rebuilt on the server by `rollout.ps1` on 2026-10-09, and a route with a shallow road (the "long" trip, truck and foot profiles) showed two paths with `td.kinds: "recommended,through_water"`. Evidence: `us-097-through-water-route-output.png`. A via request with a shallow road is tested since `f555e71` (run 37889625407).

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

### Done - US-099 Run the simple-path arrival-only search on the real graph and record its exact rate and runtime

**Result:** option A is exact for 114 of 240 searches (0.475) at a budget of 3,000,000 expansions, 0.08 s for an exact search and up to 27.6 s for an inexact one. Evidence: `us-099-option-a-real-graph-output.png`.

**What:** Run option A of `BL-027` (`marie-curie/arrival_only_simple_path.py`) on the real graph with the 3 copied replay tables. The result file records, for each vehicle limit, the exact rate, the time per pair, and the pairs that ran out of budget. Only then do `BL-027` and its plan change, citing the grid's 654 cases and the 94 and 72 counts as grid evidence ([[EP-14-routing-paper-experiments|US-090-093-routing-paper-experiments-stories]] Story 5).

**Effort:** S
**Priority:** P2
**Depends on:** the option A search and its test (written in `marie-curie/`), `real_graph.py`, and the tables in `marie-curie/edge_tables_replay_2026-10-09/`.

**Sprint:** 12, [[EP-14-routing-paper-experiments|US-090-093-routing-paper-experiments-stories]] Story 5 (US-099), in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]].

**Blocker tracking:** [[BL-027-arrival-only-reference-is-inexact-on-the-real-graph]].

**Status note:** `Done`. `BL-027` (approach 3) and the plan are updated, citing the grid's 654 scenarios, 94 earlier-arrival cases, and 72 inexact cases as grid evidence. The slow search on blocked pairs is recorded in `BL-027` and feeds `US-100`, so no separate blocker was opened.

### Active - US-100 Decide between option A closure and sticky closure for a vehicle already on the route

**What:** Read what each closure rule means for a vehicle already on the route, then record the chosen rule. On the grid, sticky closure has no route in 128 cases where option A has one and arrives later in 64. If option A can send a vehicle into a segment that floods while it is still in it, sticky closure is the safer default ([[EP-14-routing-paper-experiments|US-090-093-routing-paper-experiments-stories]] Story 6).

**Effort:** XS
**Priority:** P2
**Depends on:** `US-099` for the decision. The reading of the two rules can start now.

**Sprint:** 12, [[EP-14-routing-paper-experiments|US-090-093-routing-paper-experiments-stories]] Story 6 (US-100), in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]].

**Blocker tracking:** [[BL-027-arrival-only-reference-is-inexact-on-the-real-graph]].

**Status note:** `Not started`. This is a product choice, not a correctness issue, and the call is yours.

## Backlog

Unfinished items carried over from Sprint 8. The Done items of Sprints 9 to 11 (`US-051` to `US-054`, `US-071`, `US-072`, `US-074`, `US-075` on 2026-10-08, and `US-045`, `US-055`, `US-073`, `US-088`, `US-087`, `US-090`, `US-096` on 2026-10-09) were deleted. Their records are in the epic files and in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]].

### Done - US-069 Check the storage after the 48-hour replay to see if the retention fixes work

**Result (2026-10-10):** the hour-12 reading of the second replay passes, with all three database objects within 10 percent growth of hour 6. Evidence: `us-069-hour-12-check-output.png`.

**What:** Read the free space on C:, the size of `docker_data.vhdx`, the three database sizes (`storage-postgres-data`, `minio_custom`, `netcdf_values`), and the `flood_extent_polygon` rows at the start, at 24 hours, and at 48 hours of the replay. The check passes if the database sizes stop growing between hour 24 and hour 48 ([[EP-07-carried-over-backlog|carried-over-backlog]] Story 12).

**Effort:** S
**Priority:** P1
**Depends on:** the DAG unpaused for 48 hours ([[EP-07-carried-over-backlog|carried-over-backlog]] Story 8, `US-063`). You parked it on 2026-10-05 and said to continue after Sprint 7. It can share the DAG run that `US-045` needs.

**Sprint:** 8, carried to the Backlog on 2026-10-05 because it needs the DAG unpaused for 48 hours. [[EP-07-carried-over-backlog|carried-over-backlog]] Story 12 (US-069), in [[SP-02-routing-engine-foundations|sprint-plan-2]].

**Window:** the replay started at `2026-10-05T17:00:00Z` (00:00 +07 on 2026-10-06). Readings at 0 hours (before the unpause), 24 hours (00:00 +07 on 2026-10-07), and 48 hours (00:00 +07 on 2026-10-08).

**0-hour reading (21:32 +07, 2026-10-05):** C: free 153.6 GiB, `docker_data.vhdx` 107.48 GiB, `minio_custom` 14 GB, `flood_extent_polygon` 5,146 MB (112 rows, 8 runs), `netcdf_values` 320 MB (compressed 376 to 38 MB), `storage-postgres-data` 15.82 GB. No image builds on the server during the window.

**24-hour reading:** not recorded.

**42-hour reading (18:03 +07, 2026-10-07, i.e. 11:03Z):** C: free 104.6 GiB (-49 GiB), `docker_data.vhdx` 143.98 GiB (+36.5 GiB), `minio_custom` 8,583 MB (shrank), `flood_extent_polygon` 265 MB with rows and runs flat at 112/8 (the `FLOOD_EXTENT_KEEP_RUNS=8` cap holding), `netcdf_values` 5,399 MB total across 4 chunks, 7,426 to 980 MB compressed (grew substantially), `storage-postgres-data` 9.747 GB (shrank), `edge_depth_tables` holding exactly 3 files (`EDGE_TABLE_KEEP_RUNS=3` cap holding). No 24-hour reading exists, so this is only a 0h-vs-42h comparison, not the 24h-vs-48h comparison the pass condition asks for. The capped tables show their retention working; `docker_data.vhdx` and `netcdf_values` are still growing, so "sizes stop growing" is unproven either way. Take the 48-hour reading at replay end (2026-10-07T17:00Z) for the real comparison.

**Late reading (15:17 +07, 2026-10-08, 63 hours after the start, 15 hours after the replay ended):** C: free 105.9 GiB, `docker_data.vhdx` 143.98 GiB, `minio_custom` 8,618 MB, `flood_extent_polygon` still 112 rows in 8 runs. Against the 42-hour reading, the vhdx is unchanged and `minio_custom` grew by 35 MB. This is a partial reading: `netcdf_values` and `storage-postgres-data` were not read, and no 48-hour reading was taken at 2026-10-07T17:00Z. The new 12-hour replay writes to the same tables, so any later reading mixes the two. The 12-hour test cannot show the 24-hour to 48-hour comparison this item names, so the pass condition needs the user's decision.

**2026-10-08 decision (D-015):** the user decided the check uses the 12-hour replay and compares hour 6 with hour 12. Readings: start about 15:05 +07 (only a partial one exists, from 15:17 +07), hour 6 about 21:05 +07, hour 12 after the last simulating run at 03:00 +07 on 2026-10-09. The other conditions are unchanged. The pass mark is confirmed by the user: growth of 10 percent or less in each of the three database objects (`storage-postgres-data`, `minio_custom`, `netcdf_values`) between hour 6 and hour 12. No new size readings were taken on 2026-10-08.

**2026-10-09 reading (07:50 +07, 4.8 hours after the last simulating run):** C: free 104.5 GiB, `minio_custom` 9,191 MB, `netcdf_values` 5,713 MB (hypertable), `flood_metrics` 5,729 MB, `flood_extent_polygon` 112 rows. The hour-6 reading of D-015 was never taken, so the comparison of hour 6 with hour 12 cannot be made, and `storage-postgres-data` and `docker_data.vhdx` were not read. The item cannot close. Decide with you: accept the 0-hour and 63-hour readings as the evidence, or run one more short replay with both readings taken on time.

**2026-10-10 reading of the second replay (hour 6 at 19:30 +07 on 2026-10-09, hour 12 at 00:59 +07 on 2026-10-10):** `minio_custom` 3,158,191,251 to 2,751,065,235 bytes (-12.9 percent), `netcdf_values` in `storage-postgres` 0 rows and 56 kB at both hours, `storage-postgres-data` 4.04 GB to 3.58 GB (-11.3 percent, but the hour-12 figure is `du -sb` and the method of the hour-6 figure is not recorded), `docker_data.vhdx` 143.98 GiB at both, C: free 101.5 to 101.2 GiB, `flood_extent_polygon` 112 rows, 0 paused containers. All three database objects are within the pass mark of 10 percent growth. Full table in [[2026-10-10]]. The story is `Done` on 2026-10-10 with its evidence.

**Reminder for you:** ask Claude for the hour-6 reading at about 21:05 +07 on 2026-10-08, and the hour-12 reading after the last simulating run at 03:00 +07 on 2026-10-09. Claude cannot set a timer, so the readings happen only when you ask. Claude also needs to read `US-045` and `US-070` after 03:00 +07 (see their notes).

**Pick up:** ask Claude for the hour-6 reading at about 21:05 +07 on 2026-10-08 and the hour-12 reading after 03:15 +07 on 2026-10-09. Then run `replay.ps1 stop` and pause `flood_mapping_full`, after you confirm what `stop` resets.

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
8. [[BL-024-edge-export-has-no-node-ids|edge-export-has-no-node-ids]], `resolved` on 2026-10-09. The real-graph run of `US-092` and `US-093` waits only for the second replay.
9. [[BL-027-arrival-only-reference-is-inexact-on-the-real-graph]], open. It blocks only `US-093` and blocks no build in Sprint 13. The fix waits for your decision on the definition of the reference.
