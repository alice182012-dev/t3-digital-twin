# TODOS

## Current sprint: Sprints 9 to 11, 2026-10-05 to 2026-12-06

### Done - US-052 Integrate the engine into the backend with a flag and a fallback

**What:** The backend routes through the time-aware engine behind a flag. With the flag on, `_handle_route` uses the table, takes `t0` as the later of `valid_time` and the server clock rounded to the containing step, pins one run for the request, and returns `unknown` for a trip that ends after the last step. With the flag off the body equals today's. A missing, stale, or mismatched table falls back to today's model and the response carries a fallback flag ([[time-aware-routing-engine-stories]] Story R7).

**Effort:** M
**Priority:** P0
**Depends on:** `US-050` (the engine) and `US-043` (the Java reader), both done.

**Sprint:** 9, [[time-aware-routing-engine-stories]] Story R7 (US-052), in [[sprint-plan-3]].

**Result:** 2026-10-07, on the server (host ADMIN, branch `modular`): with the flag on, 24 real pairs ran through the deployed engine (`graphhopper` re-imported after `US-051`'s profile change, `floodmap-backend` as `routing_reader`): 37.5% of routes changed, median detour ratio 0.94, 0 crossings of a closed road, a 116-check soak run found 0 permission errors. The flag is off by default; nothing is deployed to real users. Evidence and Details in [[time-aware-routing-engine-stories]].

### Done - US-051 Add the `truck` and `foot` time-aware profiles

**What:** `truck` and `foot` requests use their own depth limits (35 cm and 40 cm) in the time-aware engine and pass the checker on the synthetic scenarios ([[time-aware-routing-engine-stories]] Story R6).

**Effort:** S
**Priority:** P1
**Depends on:** `US-050`, done. The `foot` profile was rejected by the pinned image once ([[graphhopper-vehicle-profile-rejection]]), so the first step is to check what the image accepts now.

**Sprint:** 9, [[time-aware-routing-engine-stories]] Story R6 (US-051), in [[sprint-plan-3]].

**Result:** 2026-10-07, on the server (host ADMIN): `scenario-check.sh` against the deployed image: 32 of 32 runs (4 scenarios x 4 vehicles x with/without detour) match the sticky column, 0 crossings. This change forced a GraphHopper graph re-import (profile fingerprint, not edge topology), rehearsed for the first time; the published edge-depth table stayed valid. Evidence and Details in [[time-aware-routing-engine-stories]].

### Done - US-053 Build `POST /route/departures`

**What:** An endpoint that returns each candidate departure as `clear`, `blocked`, or `unknown`, the earliest clear departure, the run, and the run's age, from the flood-free route's `edge_id` and `time` details and the depth table, with sticky closure from each candidate and a 10-minute margin. The client sends no clock value, margin, or policy ([[time-aware-routing-engine-stories]] Story R8).

**Effort:** M
**Priority:** P1
**Depends on:** `US-040`, `US-041`, and `US-042` (the table, published and kept), done, and `US-052` in the same sprint.

**Sprint:** 9, [[time-aware-routing-engine-stories]] Story R8 (US-053), in [[sprint-plan-3]].

**Result:** 2026-10-07, on the server (host ADMIN): three real trips (short, medium, long) against the deployed backend and the live `20261007T181500` table. Short/medium returned 8 candidates each (clear/unknown mix) with an earliest-clear time in 72/14 ms; the long trip returned all 8 `blocked` with no earliest-clear time in 18 ms. The `edge_id`/`time` details lined up correctly in every case. Evidence and Details in [[time-aware-routing-engine-stories]].

### Done - US-054 Show "wait until" in the no-route alert

**What:** When a route request fails with no connection, the client asks `POST /route/departures` and the alert shows a loading line, then "The usual route is clear from HH:MM (forecast run HH:MM)", or "No safe route in the next 2 hours. Check again after the next forecast run." A clear route shows no advice. A table that is unavailable shows "timing check unavailable". The alert keeps its advice to reach the safest location or stay put, and says "clear in the forecast", not "safe" ([[time-aware-routing-engine-stories]] Story R9).

**Effort:** S
**Priority:** P1
**Depends on:** `US-053` (the endpoint, `Reviewed`) and [[frontend-polish]] Story 4 (the no-route state, `Done`).

**Sprint:** 10, [[time-aware-routing-engine-stories]] Story R9 (US-054), in [[sprint-plan-3]].

**Result:** 2026-10-07, on the server (host ADMIN): drove the deployed frontend at `localhost:8082` by hand (real `type`/`Enter`, not URL params) with the pair `21.0215, 105.7610` to `21.0230, 105.7650` for `motorbike`, currently blocked. `POST /route` failed (400), the frontend called `POST /route/departures` automatically, and the alert rendered exactly: "No safe route available. Please consider getting to the safest location or stay where you are." and "No safe route in the next 2 hours. Check again after the next forecast run." Evidence and Details in [[time-aware-routing-engine-stories]].

### Active - US-055 Prove the engine on the server and roll it out

**What:** Evidence on the server before the flag goes on. The four scenarios for the four vehicles pass the checker on the deployed image and a real run. The p50 and p95 of `POST /route` stay within 2 times the baseline of `US-046`. A fixed set of pairs run against today's model and the reference gives the share of routes that change and the median detour ratio. The tooling is built first, so the server needs one deploy and one run ([[time-aware-routing-engine-stories]] Story R10).

**Effort:** M
**Priority:** P0
**Depends on:** `US-051`, `US-052`, `US-053`, `US-054` and `US-045`. The latency factor of 2 was set on 2026-10-02. The server run waits for the end of the 48-hour replay, because no image is built on the server until then.

**Sprint:** 10, [[time-aware-routing-engine-stories]] Story R10 (US-055), in [[sprint-plan-3]].

**Status note:** `In progress`. On 2026-10-07 (host ADMIN, branch `modular`), `rollout.ps1` ran (not from the Mac as written, run locally since this session is the server): the graphhopper/backend/frontend images built, graphhopper needed a graph re-import first (US-051's profile change, see [[graph-reimport-procedure]]), then every check that doesn't need the DAG passed — `compare` (37.5% changed, median detour 0.94), `crossings` (0), `departures` (3/3 trips), `latency` (all 6 cells within 2x the `US-046` baseline), `scenario-check.sh` (32/32), and a real browser check of the no-route alert. `US-051`, `US-052`, `US-053`, `US-054`, and `US-072` are now `Done` on this evidence. Only `US-045` is left among `US-055`'s own dependencies, and it's deferred with the rest of the DAG-timing work (`US-073`'s trigger/timing, `US-070`'s confirmation, `US-069`) until after Sprint 11, at the user's request, so they run together.

### Active - US-070 Stop a slow sampling step from holding the database

**What:** Task `9c` ran over 770 s in one sampling step during the replay. It now analyzes `flood_depth_raster_tile` first and cancels a step past 120 s ([[edge-depth-table-stories]] Story E8).

**Effort:** S
**Priority:** P1
**Depends on:** `US-041`, done.

**Sprint:** 10, [[edge-depth-table-stories]] Story E8 (US-070), in [[sprint-plan-3]].

**Blocker tracking:** [[9c-sampling-step-runs-over-770-seconds]].

**Status note:** built and pushed as `5e358bf`, 133 tests pass. The server is at `4d262ef`, which contains it. Run `20261006T104500` took 51.1 s and its `ANALYZE` ran. The blocker closes after several more 9c runs under load stay near 50 s.

### Done - US-071 Write the output contract and a test that checks it against the live schema

**What:** A contract page that states what routing reads from the core: the tables, the edge depth `.bin`, the vehicle thresholds, the time convention, the keys, the retention, and `flood_extent_step.published_at` as the readiness flag. A test compares the page with the live schema ([[routing-first-consumer-stories]] Story C1, plan [[routing-first-consumer-contract]]).

**Effort:** M
**Priority:** P1
**Depends on:** None. `US-072`, `US-073`, and `US-075` read its table list, so it goes first.

**Sprint:** 11, [[routing-first-consumer-stories]] Story C1 (US-071), in [[sprint-plan-3]].

**Result:** 2026-10-07, on the server (host ADMIN), a one-off read-only container against the live database: "live schema matches the contract for 5 tables, ok." A deliberately wrong page fails as expected. Evidence and Details in [[routing-first-consumer-stories]].

### Done - US-072 Run the routing backend on a read-only database role

**What:** The backend connects with a role that can only read the contract tables. Every endpoint works on it, and an `INSERT` into any core table fails with a permission error ([[routing-first-consumer-stories]] Story C2).

**Effort:** S
**Priority:** P1
**Depends on:** `US-071` (the table list). The server run waits for `US-055` and the end of the replay.

**Sprint:** 11, [[routing-first-consumer-stories]] Story C2 (US-072), in [[sprint-plan-3]].

**Result:** 2026-10-07, on the server (host ADMIN): role created (reads 5 contract tables), `floodmap-backend` recreated as `routing_reader`, `test_reader_role.py` passed live (reads work, every `INSERT` refused, a non-contract table refused), 5 endpoints checked by hand, and a 116-check soak run found 0 permission errors. Evidence and Details in [[routing-first-consumer-stories]].

### Active - US-073 Move the routing-owned tasks into their own DAG, triggered by the core's published output

**What:** `9b_load_depth_raster` emits an Airflow asset event with the run id. A DAG `routing_adapter` scheduled on that asset runs `load_road_segments`, `flood_on_roads`, and `9c_build_edge_depth_table`. A routing failure leaves the core run green, and 9c still ends within 5 minutes of `3_calculate_depth`. The fallback is a TaskGroup in the same DAG ([[routing-first-consumer-stories]] Story C3).

**Effort:** M
**Priority:** P2
**Depends on:** `US-071` (the contract names the signal). The server timing waits for `US-055`, because the proof and the replay use today's DAG shape. Task ids move to a new `dag_id`, so check `scripts/pipeline_margins` and the proof tooling first.

**Sprint:** 11, [[routing-first-consumer-stories]] Story C3 (US-073), in [[sprint-plan-3]].

**Status note:** `Reviewed`. Built on `modular` (`77169c3`). Real Airflow 3.1.7 on the server serialized both DAGs, and `dags list-import-errors` is clean with `routing_adapter` registered. Pool `routing_adapter` created 2026-10-07 (step 5 of [[sprint-11-server-rollout]]). Unpausing the core DAG for about an hour to read the asset events and measure 9c (steps 9 to 12) is deferred until after Sprint 11, at the user's request, so it runs together with the rest of the analysis.

### Done - US-074 Give the vehicle thresholds one owner

**What:** The vehicle depth limits live in one place. Today they are in `flood_utils.py` and again as `td_limit_cm` in `config.yml`, and a test keeps the two equal ([[routing-first-consumer-stories]] Story C4).

**Effort:** S
**Priority:** P2
**Depends on:** None.

**Sprint:** 11, [[routing-first-consumer-stories]] Story C4 (US-074), in [[sprint-plan-3]].

**Result:** 2026-10-07, on the server (host ADMIN): `test_no_source_file_defines_the_limits_again ... ok`. `VEHICLE_PROFILES` in `flood_utils.py` is the owner, the `td_limit_cm` cross-check still passes, and the Airflow container import stays unchanged. Evidence and Details in [[routing-first-consumer-stories]].

### Done - US-075 Fail a test when the backend reads a table outside the contract

**What:** A test fails when the backend queries a table that the contract does not list ([[routing-first-consumer-stories]] Story C5).

**Effort:** S
**Priority:** P2
**Depends on:** `US-071` (the table list).

**Sprint:** 11, [[routing-first-consumer-stories]] Story C5 (US-075), in [[sprint-plan-3]].

**Result:** 2026-10-07, on the server (host ADMIN): "backend reads only contract tables (5 listed) ... reads ['flood_depth_raster_tile', 'flood_extent_polygon', 'flood_extent_step', 'flood_road_values'] ... ok." Evidence and Details in [[routing-first-consumer-stories]].

## Backlog

Unfinished items carried over from Sprint 8. The Done items of Sprints 4 to 8 were deleted at the 2026-10-07 rollover.

### Active - US-045 Prove the table on the server

**What:** Measure the build time, the file size, and the edge count of the table task on a real run on the server, check 20 edges against `ST_Value`, and record the numbers in [[edge-depth-table]], replacing the guessed size. If the build time exceeds the limit, log a blocker ([[edge-depth-table-stories]] Story E7).

**Effort:** M
**Priority:** P0
**Depends on:** `US-041` and `US-042`, both done. The limit is 5 minutes after the end of `3_calculate_depth`, never delaying the tile task, so it needs a live DAG run of task `9c`, which means the DAG unpaused. The unloaded numbers so far are 42.0 s, 1,085,487 bytes, and 160 of 160 values equal.

**Sprint:** 8, carried to the Backlog on 2026-10-05 because it needs the DAG unpaused for the 48-hour window. [[edge-depth-table-stories]] Story E7 (US-045), in [[sprint-plan-2]].

**Status note:** not ready to close. `routing_adapter` (the DAG hosting 9c, `US-073`) only started running on `modular` on 2026-10-07 16:00 +07, about 2 hours before this check, so only one real 9c run exists despite 364 successful `flood_mapping_full` runs in the replay: 60.1 s build, 67,833 edges, 1,085,487 bytes, matching the 2026-10-06 numbers. The gap from the end of `3_calculate_depth` to the end of 9c was 8.21 minutes, over the 5-minute limit, but with n=1 this cannot be told apart from the new DAG's cold-start/backlog catch-up. `table_timing.ps1` has no `ST_Value` spot-check at all (checked its 210 lines), so that acceptance criterion needs separate tooling. Re-run after the replay ends and `routing_adapter` has accumulated several more runs.

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

## Blockers for the next sprint

The next sprint is Sprint 12, 2026-12-07 to 2026-12-13, in [[sprint-plan-3]]. It is spare capacity, and no story is placed in it.

Checked on 2026-10-07 against `sprint-plan-3`: no row to check.

Any blocker stops Sprint 12: None

The unresolved blockers are:

1. [[route-panel-stuck-on-loading-bars]], monitoring.
2. [[map-shows-forecast-not-now]], monitoring.
3. [[routing-not-time-aware]], which `US-055` resolves.
4. [[9c-sampling-step-runs-over-770-seconds]], monitoring, fixed in code by `US-070`. It blocks no build.
5. [[place-name-slow-after-map-tap]], which blocks no build. Its story `US-061` has no sprint.
