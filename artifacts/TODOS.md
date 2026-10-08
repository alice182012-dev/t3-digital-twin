# TODOS

## Current sprint: Sprints 9 to 11, 2026-10-05 to 2026-12-06

### Active - US-055 Prove the engine on the server and roll it out

**What:** Evidence on the server before the flag goes on. The four scenarios for the four vehicles pass the checker on the deployed image and a real run. The p50 and p95 of `POST /route` stay within 2 times the baseline of `US-046`. A fixed set of pairs run against today's model and the reference gives the share of routes that change and the median detour ratio. The tooling is built first, so the server needs one deploy and one run ([[time-aware-routing-engine-stories]] Story R10).

**Effort:** M
**Priority:** P0
**Depends on:** `US-051`, `US-052`, `US-053`, `US-054` and `US-045`. The latency factor of 2 was set on 2026-10-02. The server run waits for the end of the 48-hour replay, because no image is built on the server until then.

**Sprint:** 10, [[time-aware-routing-engine-stories]] Story R10 (US-055), in [[sprint-plan-3]].

**Status note:** `In progress`. On 2026-10-07 (host ADMIN, branch `modular`), `rollout.ps1` ran (not from the Mac as written, run locally since this session is the server): the graphhopper/backend/frontend images built, graphhopper needed a graph re-import first (US-051's profile change, see [[graph-reimport-procedure]]), then every check that doesn't need the DAG passed — `compare` (37.5% changed, median detour 0.94), `crossings` (0), `departures` (3/3 trips), `latency` (all 6 cells within 2x the `US-046` baseline), `scenario-check.sh` (32/32), and a real browser check of the no-route alert. `US-051`, `US-052`, `US-053`, `US-054`, and `US-072` are now `Done` on this evidence. Only `US-045` is left among `US-055`'s own dependencies, and it's deferred with the rest of the DAG-timing work (`US-073`'s trigger/timing, `US-070`'s confirmation, `US-069`) until after Sprint 11, at the user's request, so they run together. That run started on 2026-10-08 (see `US-045`).

**Pick up after `US-045` closes:** read the `US-045` result, then decide with you whether `TIME_AWARE_ROUTING` stays off at rest (it reads `false` on the server) or the next `rollout.ps1` runs with `-LeaveOn`.

### Active - US-070 Stop a slow sampling step from holding the database

**What:** Task `9c` ran over 770 s in one sampling step during the replay. It now analyzes `flood_depth_raster_tile` first and cancels a step past 120 s ([[edge-depth-table-stories]] Story E8).

**Effort:** S
**Priority:** P1
**Depends on:** `US-041`, done.

**Sprint:** 10, [[edge-depth-table-stories]] Story E8 (US-070), in [[sprint-plan-3]].

**Blocker tracking:** [[9c-sampling-step-runs-over-770-seconds]].

**Status note:** built and pushed as `5e358bf`, 133 tests pass. The server is at `4d262ef`, which contains it. Run `20261006T104500` took 51.1 s and its `ANALYZE` ran. The blocker closes after several more 9c runs under load stay near 50 s. The 12-hour replay that started on 2026-10-08 supplies those runs.

**2026-10-08 readings:** over 9 runs `9c` took 46 to 64 s (63.1 s at most), and no step passed the 120 s cancel. The blocker closes when `9c` stays near 50 s, and it rose by about 2 s per run, so the item stays open until the numbers level off after 03:00 +07 on 2026-10-09.

**Pick up after 03:00 +07 on 2026-10-09:** read the `9c` durations of all 42 runs from the Airflow metadata database (`task_instance`, `dag_id='routing_adapter'`). Close the blocker if they level off near 50 s. The readings of 2026-10-08 rose from 46 to 64 s over 9 runs.

### Active - US-073 Move the routing-owned tasks into their own DAG, triggered by the core's published output

**What:** `9b_load_depth_raster` emits an Airflow asset event with the run id. A DAG `routing_adapter` scheduled on that asset runs `load_road_segments`, `flood_on_roads`, and `9c_build_edge_depth_table`. A routing failure leaves the core run green, and 9c still ends within 5 minutes of `3_calculate_depth`. The fallback is a TaskGroup in the same DAG ([[routing-first-consumer-stories]] Story C3).

**Effort:** M
**Priority:** P2
**Depends on:** `US-071` (the contract names the signal). The server timing waits for `US-055`, because the proof and the replay use today's DAG shape. Task ids move to a new `dag_id`, so check `scripts/pipeline_margins` and the proof tooling first.

**Sprint:** 11, [[routing-first-consumer-stories]] Story C3 (US-073), in [[sprint-plan-3]].

**Status note:** `Reviewed`. Built on `modular` (`77169c3`). Real Airflow 3.1.7 on the server serialized both DAGs, and `dags list-import-errors` is clean with `routing_adapter` registered. Pool `routing_adapter` created 2026-10-07 (step 5 of [[sprint-11-server-rollout]]). Unpausing the core DAG for about an hour to read the asset events and measure 9c (steps 9 to 12) is deferred until after Sprint 11, at the user's request, so it runs together with the rest of the analysis. The core DAG was unpaused on 2026-10-08 at about 15:05 +07 for the 12-hour replay, so the asset events and the 9c timing are read after 03:00 +07 on 2026-10-09.

**2026-10-08 readings:** `routing_adapter` ran `9c` after each of 9 core runs (9 of 9, a 10th was running), and the gap to the end of `3_calculate_depth` stayed under 5 minutes (see `US-045`). Not observed: a routing failure leaving the core run green, because none occurred.

**Pick up after 03:00 +07 on 2026-10-09:** confirm every simulating run triggered one `routing_adapter` run (42 of 42) and the calc-to-9c gap stayed under 5 minutes. A routing failure leaving the core run green is still unobserved, so decide whether a unit test is enough for `Done`.

### Active - US-094 Archive `results_3di.nc` and a run record to D: when the pipeline reads real rain

**What:** A new task after `2_download_results` copies `RESULT_DIR/<sim_id>/results_3di.nc` and a run record (`sim_id`, rain input, model revision, graph hash, run timestamp) to an archive folder on D:. It skips when `FLOOD_TEST_RAIN_CSV` or `FLOOD_TEST_RAIN_MM_HR` is set. `9_build_flood_tiles` waits for it, so the 24-hour cleanup cannot delete the file first. The task logs the free space of D: after each copy and fails loudly below a floor (proposed 50 GB, to confirm with you). The daily growth in GB is measured ([[US-094-095-archive-and-netcdf-retirement-stories]] Story 1, D-016).

**Effort:** M
**Priority:** P1
**Depends on:** none to build. A one-off run with the real Tomorrow.io forecast counts as the proof (your decision of 2026-10-08), and it waits for a real forecast above the rain gate (5 mm/h), with no gate change and no override (your choice of 2026-10-08). `US-095` and `US-086` wait for it. The folder is `D:\airflow_new_data\archive`, confirmed by you on 2026-10-08.

**Sprint:** 10, [[US-094-095-archive-and-netcdf-retirement-stories]] Story 1 (US-094), in [[sprint-plan-3]].

**Status note:** `Not started`. It blocks `US-095` and `US-086`.

### Active - US-095 Retire the `netcdf_values` ingest

**What:** Remove task `3b_upload_netcdf_postgres`, the tables `netcdf_values`, `mesh_elements`, and `netcdf_variable_catalog`, the two `storage-postgres` tables `netcdf_files` and `netcdf_variables`, and the scripts and tests that use them. `0b_ensure_schema` still creates the three empty tables. The server drop runs in order (`netcdf_values`, then the catalog) and records the `timescaledb` size and the C: free space ([[US-094-095-archive-and-netcdf-retirement-stories]] Story 2, D-018).

**Effort:** M
**Priority:** P1
**Depends on:** `US-094` proven on real rain. The server drop needs your explicit go.

**Sprint:** 11, [[US-094-095-archive-and-netcdf-retirement-stories]] Story 2 (US-095), in [[sprint-plan-3]].

**Status note:** `Not started`.

## Backlog

Unfinished items carried over from Sprint 8. The Done items of Sprints 9 to 11 (`US-051` to `US-054`, `US-071`, `US-072`, `US-074`, `US-075`) were deleted at the 2026-10-08 rollover. Their records are in the epic files and in [[sprint-plan-3]].

### Active - US-045 Prove the table on the server

**What:** Measure the build time, the file size, and the edge count of the table task on a real run on the server, check 20 edges against `ST_Value`, and record the numbers in [[edge-depth-table]], replacing the guessed size. If the build time exceeds the limit, log a blocker ([[edge-depth-table-stories]] Story E7).

**Effort:** M
**Priority:** P0
**Depends on:** `US-041` and `US-042`, both done. The limit is 5 minutes after the end of `3_calculate_depth`, never delaying the tile task, so it needs a live DAG run of task `9c`, which means the DAG unpaused. The unloaded numbers so far are 42.0 s, 1,085,487 bytes, and 160 of 160 values equal.

**Sprint:** 8, carried to the Backlog on 2026-10-05 because it needs the DAG unpaused for the 48-hour window. [[edge-depth-table-stories]] Story E7 (US-045), in [[sprint-plan-2]].

**Status note:** not ready to close. `routing_adapter` (the DAG hosting 9c, `US-073`) only started running on `modular` on 2026-10-07 16:00 +07, about 2 hours before this check, so only one real 9c run exists despite 364 successful `flood_mapping_full` runs in the replay: 60.1 s build, 67,833 edges, 1,085,487 bytes, matching the 2026-10-06 numbers. The gap from the end of `3_calculate_depth` to the end of 9c was 8.21 minutes, over the 5-minute limit, but with n=1 this cannot be told apart from the new DAG's cold-start/backlog catch-up. `table_timing.ps1` has no `ST_Value` spot-check, but `scripts/edge_depth/spot_check.py` does (correction of 2026-10-08). Re-run after the replay ends and `routing_adapter` has accumulated several more runs.

**2026-10-08 update:** a new 12-hour replay (`hanoi_20260916_storm.csv`, gate 5 mm/h) is on the server and `flood_mapping_full` was unpaused at about 15:05 +07. The first simulating run is 15:45 +07 and the last is 03:00 +07 on 2026-10-09: 42 runs in 2 chains. Each simulating run triggers `routing_adapter`, so the 12 hours should give the several 9c runs this item needs. Read the gaps after 03:00 +07, and build the `ST_Value` spot-check tooling before then.

**2026-10-08 readings (17:08 +07, 9 successful runs of `flood_mapping_full`, 9 of `9c`):** build time 55.5 s on average, 63.1 s at most. The spot check (`spot_check.py`, 20 edges, run on the worker against the latest table `20261008T171500.bin`, 1,085,487 bytes) passed: 160 of 160 values equal a direct `ST_Value` reading. The gap from the end of `3_calculate_depth` to the end of `9c` was 2.69 to 3.42 minutes, under the 5-minute limit, but it grows with every run (2.69, 2.85, 2.91, 3.06, 3.10, 3.21, 3.30, 3.39, 3.42). The cause is the tasks before it: `9b_load_depth_raster` rose from 115 to 141 s, the tile build from 66 to 135 s, and `9c` from 46 to 64 s, while `3_calculate_depth` stayed at about 173 s. A straight-line extrapolation crosses 5 minutes near run 26, which is a projection, not a measurement. Not closed: read the same numbers after 03:00 +07 on 2026-10-09 to see whether the growth stops, then record them in [[edge-depth-table]] and take the evidence screenshot.

**Pick up after 03:00 +07 on 2026-10-09:** (1) re-run the timing query for all 42 runs and check the growth stopped and the gap stays under 5 minutes (it was 2.69 to 3.42 over 9 runs and rising); (2) re-run `spot_check.py` on the latest table; (3) record the numbers in [[edge-depth-table]], replacing the guessed size; (4) take the evidence screenshot; (5) copy a few edge depth tables off the server for `US-091` to `US-093`, because only the newest 3 stay. Copying a mid-replay snapshot is safer than waiting.

### Active - US-069 Check the storage after the 48-hour replay to see if the retention fixes work

**What:** Read the free space on C:, the size of `docker_data.vhdx`, the three database sizes (`storage-postgres-data`, `minio_custom`, `netcdf_values`), and the `flood_extent_polygon` rows at the start, at 24 hours, and at 48 hours of the replay. The check passes if the database sizes stop growing between hour 24 and hour 48 ([[carried-over-backlog]] Story 12).

**Effort:** S
**Priority:** P1
**Depends on:** the DAG unpaused for 48 hours ([[carried-over-backlog]] Story 8, `US-063`). You parked it on 2026-10-05 and said to continue after Sprint 7. It can share the DAG run that `US-045` needs.

**Sprint:** 8, carried to the Backlog on 2026-10-05 because it needs the DAG unpaused for 48 hours. [[carried-over-backlog]] Story 12 (US-069), in [[sprint-plan-2]].

**Window:** the replay started at `2026-10-05T17:00:00Z` (00:00 +07 on 2026-10-06). Readings at 0 hours (before the unpause), 24 hours (00:00 +07 on 2026-10-07), and 48 hours (00:00 +07 on 2026-10-08).

**0-hour reading (21:32 +07, 2026-10-05):** C: free 153.6 GiB, `docker_data.vhdx` 107.48 GiB, `minio_custom` 14 GB, `flood_extent_polygon` 5,146 MB (112 rows, 8 runs), `netcdf_values` 320 MB (compressed 376 to 38 MB), `storage-postgres-data` 15.82 GB. No image builds on the server during the window.

**24-hour reading:** not recorded.

**42-hour reading (18:03 +07, 2026-10-07, i.e. 11:03Z):** C: free 104.6 GiB (-49 GiB), `docker_data.vhdx` 143.98 GiB (+36.5 GiB), `minio_custom` 8,583 MB (shrank), `flood_extent_polygon` 265 MB with rows and runs flat at 112/8 (the `FLOOD_EXTENT_KEEP_RUNS=8` cap holding), `netcdf_values` 5,399 MB total across 4 chunks, 7,426 to 980 MB compressed (grew substantially), `storage-postgres-data` 9.747 GB (shrank), `edge_depth_tables` holding exactly 3 files (`EDGE_TABLE_KEEP_RUNS=3` cap holding). No 24-hour reading exists, so this is only a 0h-vs-42h comparison, not the 24h-vs-48h comparison the pass condition asks for. The capped tables show their retention working; `docker_data.vhdx` and `netcdf_values` are still growing, so "sizes stop growing" is unproven either way. Take the 48-hour reading at replay end (2026-10-07T17:00Z) for the real comparison.

**Late reading (15:17 +07, 2026-10-08, 63 hours after the start, 15 hours after the replay ended):** C: free 105.9 GiB, `docker_data.vhdx` 143.98 GiB, `minio_custom` 8,618 MB, `flood_extent_polygon` still 112 rows in 8 runs. Against the 42-hour reading, the vhdx is unchanged and `minio_custom` grew by 35 MB. This is a partial reading: `netcdf_values` and `storage-postgres-data` were not read, and no 48-hour reading was taken at 2026-10-07T17:00Z. The new 12-hour replay writes to the same tables, so any later reading mixes the two. The 12-hour test cannot show the 24-hour to 48-hour comparison this item names, so the pass condition needs the user's decision.

**2026-10-08 decision (D-015):** the user decided the check uses the 12-hour replay and compares hour 6 with hour 12. Readings: start about 15:05 +07 (only a partial one exists, from 15:17 +07), hour 6 about 21:05 +07, hour 12 after the last simulating run at 03:00 +07 on 2026-10-09. The other conditions are unchanged. The pass mark is confirmed by the user: growth of 10 percent or less in each of the three database objects (`storage-postgres-data`, `minio_custom`, `netcdf_values`) between hour 6 and hour 12. No new size readings were taken on 2026-10-08.

**Reminder for you:** ask Claude for the hour-6 reading at about 21:05 +07 on 2026-10-08, and the hour-12 reading after the last simulating run at 03:00 +07 on 2026-10-09. Claude cannot set a timer, so the readings happen only when you ask. Claude also needs to read `US-045` and `US-070` after 03:00 +07 (see their notes).

**Pick up:** ask Claude for the hour-6 reading at about 21:05 +07 on 2026-10-08 and the hour-12 reading after 03:15 +07 on 2026-10-09. Then run `replay.ps1 stop` and pause `flood_mapping_full`, after you confirm what `stop` resets.

## Blockers for the next sprint

The next sprint is Sprint 12, planned for 2026-12-07 to 2026-12-13 in [[sprint-plan-3]]. The user will start it on 2026-10-09, 59 days early. It holds 8 rows: `US-086` to `US-093`, four M and four S. The frontend rows `US-076` to `US-085` and `US-033` moved out on 2026-10-08 ([[sprint-plan-4]]). Its rows enter this file when the sprint starts, not before (rule 9). `US-088` and `US-089` started early and are tracked in [[rain-replay-test-environment-stories]]: `US-088` has its event file (`hanoi_20260916_storm.csv`) and waits for its evidence screenshot, and `US-089` ran `start` on the server on 2026-10-08 and waits for `stop` and a screenshot.

Checked on 2026-10-08 against `sprint-plan-3`: Sprint 12's rows depend on no open blocker. The NASA download that `US-088` needed ran on the Mac with a token, because the Earthdata login host is unreachable from the user's network. The server holds a 12-hour replay until 03:00 +07 on 2026-10-09, and no Sprint 12 row waits on it.

Any blocker stops Sprint 12: None

The unresolved blockers are:

1. [[route-panel-stuck-on-loading-bars]], monitoring.
2. [[map-shows-forecast-not-now]], monitoring.
3. [[routing-not-time-aware]], which `US-055` resolves.
4. [[9c-sampling-step-runs-over-770-seconds]], monitoring, fixed in code by `US-070`. It blocks no build.
5. [[place-name-slow-after-map-tap]], which blocks no build. Its story `US-061` has no sprint.
