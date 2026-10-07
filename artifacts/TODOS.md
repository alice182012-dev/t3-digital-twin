# TODOS

## Current sprint: Sprints 9 to 11, 2026-10-05 to 2026-12-06

### Active - US-052 Integrate the engine into the backend with a flag and a fallback

**What:** The backend routes through the time-aware engine behind a flag. With the flag on, `_handle_route` uses the table, takes `t0` as the later of `valid_time` and the server clock rounded to the containing step, pins one run for the request, and returns `unknown` for a trip that ends after the last step. With the flag off the body equals today's. A missing, stale, or mismatched table falls back to today's model and the response carries a fallback flag ([[time-aware-routing-engine-stories]] Story R7).

**Effort:** M
**Priority:** P0
**Depends on:** `US-050` (the engine) and `US-043` (the Java reader), both done.

**Sprint:** 9, [[time-aware-routing-engine-stories]] Story R7 (US-052), in [[sprint-plan-3]].

**Status note:** `Reviewed`. Built and tested (plan [[time-aware-backend-integration]]). The flag is off by default and nothing is deployed. The proof on the server is `US-055`, after the 48-hour window.

### Active - US-051 Add the `truck` and `foot` time-aware profiles

**What:** `truck` and `foot` requests use their own depth limits (35 cm and 40 cm) in the time-aware engine and pass the checker on the synthetic scenarios ([[time-aware-routing-engine-stories]] Story R6).

**Effort:** S
**Priority:** P1
**Depends on:** `US-050`, done. The `foot` profile was rejected by the pinned image once ([[graphhopper-vehicle-profile-rejection]]), so the first step is to check what the image accepts now.

**Sprint:** 9, [[time-aware-routing-engine-stories]] Story R6 (US-051), in [[sprint-plan-3]].

**Status note:** `Reviewed`. `truck` (35 cm) and `foot` (40 cm) are in `config.yml`, and the scenario report runs 32 cases. The server run is part of `US-055`.

### Active - US-053 Build `POST /route/departures`

**What:** An endpoint that returns each candidate departure as `clear`, `blocked`, or `unknown`, the earliest clear departure, the run, and the run's age, from the flood-free route's `edge_id` and `time` details and the depth table, with sticky closure from each candidate and a 10-minute margin. The client sends no clock value, margin, or policy ([[time-aware-routing-engine-stories]] Story R8).

**Effort:** M
**Priority:** P1
**Depends on:** `US-040`, `US-041`, and `US-042` (the table, published and kept), done, and `US-052` in the same sprint.

**Sprint:** 9, [[time-aware-routing-engine-stories]] Story R8 (US-053), in [[sprint-plan-3]].

**Status note:** `Reviewed`. The endpoint is built and tested (plan [[route-departures-endpoint]]). The check on a real route is part of `US-055`.

### Active - US-054 Show "wait until" in the no-route alert

**What:** When a route request fails with no connection, the client asks `POST /route/departures` and the alert shows a loading line, then "The usual route is clear from HH:MM (forecast run HH:MM)", or "No safe route in the next 2 hours. Check again after the next forecast run." A clear route shows no advice. A table that is unavailable shows "timing check unavailable". The alert keeps its advice to reach the safest location or stay put, and says "clear in the forecast", not "safe" ([[time-aware-routing-engine-stories]] Story R9).

**Effort:** S
**Priority:** P1
**Depends on:** `US-053` (the endpoint, `Reviewed`) and [[frontend-polish]] Story 4 (the no-route state, `Done`).

**Sprint:** 10, [[time-aware-routing-engine-stories]] Story R9 (US-054), in [[sprint-plan-3]].

**Status note:** `Reviewed`. Built and tested (plan [[wait-until-alert]]). The check in a browser against the real backend is part of `US-055`.

### Active - US-055 Prove the engine on the server and roll it out

**What:** Evidence on the server before the flag goes on. The four scenarios for the four vehicles pass the checker on the deployed image and a real run. The p50 and p95 of `POST /route` stay within 2 times the baseline of `US-046`. A fixed set of pairs run against today's model and the reference gives the share of routes that change and the median detour ratio. The tooling is built first, so the server needs one deploy and one run ([[time-aware-routing-engine-stories]] Story R10).

**Effort:** M
**Priority:** P0
**Depends on:** `US-051`, `US-052`, `US-053`, `US-054` and `US-045`. The latency factor of 2 was set on 2026-10-02. The server run waits for the end of the 48-hour replay, because no image is built on the server until then.

**Sprint:** 10, [[time-aware-routing-engine-stories]] Story R10 (US-055), in [[sprint-plan-3]].

**Status note:** `In progress`. The tooling is built (`scripts/routing_proof/`, plan [[engine-server-proof-and-rollout]]). The evidence is one run of `rollout.ps1` on the server after the replay ends.

### Active - US-070 Stop a slow sampling step from holding the database

**What:** Task `9c` ran over 770 s in one sampling step during the replay. It now analyzes `flood_depth_raster_tile` first and cancels a step past 120 s ([[edge-depth-table-stories]] Story E8).

**Effort:** S
**Priority:** P1
**Depends on:** `US-041`, done.

**Sprint:** 10, [[edge-depth-table-stories]] Story E8 (US-070), in [[sprint-plan-3]].

**Blocker tracking:** [[9c-sampling-step-runs-over-770-seconds]].

**Status note:** built and pushed as `5e358bf`, 133 tests pass. The server is at `4d262ef`, which contains it. Run `20261006T104500` took 51.1 s and its `ANALYZE` ran. The blocker closes after several more 9c runs under load stay near 50 s.

### Active - US-071 Write the output contract and a test that checks it against the live schema

**What:** A contract page that states what routing reads from the core: the tables, the edge depth `.bin`, the vehicle thresholds, the time convention, the keys, the retention, and `flood_extent_step.published_at` as the readiness flag. A test compares the page with the live schema ([[routing-first-consumer-stories]] Story C1, plan [[routing-first-consumer-contract]]).

**Effort:** M
**Priority:** P1
**Depends on:** None. `US-072`, `US-073`, and `US-075` read its table list, so it goes first.

**Sprint:** 11, [[routing-first-consumer-stories]] Story C1 (US-071), in [[sprint-plan-3]].

**Status note:** `Reviewed`. Built on branch `modular` (commits `888c86e`, `27e8957`). The live schema and key check passed in the server's backend container on 2026-10-07 and failed on a deliberately wrong page. Evidence screenshot pending.

### Active - US-072 Run the routing backend on a read-only database role

**What:** The backend connects with a role that can only read the contract tables. Every endpoint works on it, and an `INSERT` into any core table fails with a permission error ([[routing-first-consumer-stories]] Story C2).

**Effort:** S
**Priority:** P1
**Depends on:** `US-071` (the table list). The server run waits for `US-055` and the end of the replay.

**Sprint:** 11, [[routing-first-consumer-stories]] Story C2 (US-072), in [[sprint-plan-3]].

**Status note:** `Reviewed`. Built on `modular` (`56426ed`). Offline tests pass. The role script, the live test, and the endpoint checks run on the server after the replay, with the steps in the commit report.

### Active - US-073 Move the routing-owned tasks into their own DAG, triggered by the core's published output

**What:** `9b_load_depth_raster` emits an Airflow asset event with the run id. A DAG `routing_adapter` scheduled on that asset runs `load_road_segments`, `flood_on_roads`, and `9c_build_edge_depth_table`. A routing failure leaves the core run green, and 9c still ends within 5 minutes of `3_calculate_depth`. The fallback is a TaskGroup in the same DAG ([[routing-first-consumer-stories]] Story C3).

**Effort:** M
**Priority:** P2
**Depends on:** `US-071` (the contract names the signal). The server timing waits for `US-055`, because the proof and the replay use today's DAG shape. Task ids move to a new `dag_id`, so check `scripts/pipeline_margins` and the proof tooling first.

**Sprint:** 11, [[routing-first-consumer-stories]] Story C3 (US-073), in [[sprint-plan-3]].

**Status note:** `Reviewed`. Built on `modular` (`77169c3`). Real Airflow 3.1.7 on the server serialized both DAGs. No event has fired and 9c's 5-minute limit is not measured. The pool `routing_adapter` must be created by hand first.

### Active - US-074 Give the vehicle thresholds one owner

**What:** The vehicle depth limits live in one place. Today they are in `flood_utils.py` and again as `td_limit_cm` in `config.yml`, and a test keeps the two equal ([[routing-first-consumer-stories]] Story C4).

**Effort:** S
**Priority:** P2
**Depends on:** None.

**Sprint:** 11, [[routing-first-consumer-stories]] Story C4 (US-074), in [[sprint-plan-3]].

**Status note:** `Reviewed`. Built on `modular` (`0ab6028`). `VEHICLE_PROFILES` in `flood_utils.py` is the owner, and guard tests fail if a second copy or a broken mount appears.

### Active - US-075 Fail a test when the backend reads a table outside the contract

**What:** A test fails when the backend queries a table that the contract does not list ([[routing-first-consumer-stories]] Story C5).

**Effort:** S
**Priority:** P2
**Depends on:** `US-071` (the table list).

**Sprint:** 11, [[routing-first-consumer-stories]] Story C5 (US-075), in [[sprint-plan-3]].

**Status note:** `Reviewed`. Built on `modular` (`892afe3`). The guard reads the backend's SQL with `ast` and fails on a table outside the contract.

## Backlog

Unfinished items carried over from Sprint 8. The Done items of Sprints 4 to 8 were deleted at the 2026-10-07 rollover.

### Active - US-045 Prove the table on the server

**What:** Measure the build time, the file size, and the edge count of the table task on a real run on the server, check 20 edges against `ST_Value`, and record the numbers in [[edge-depth-table]], replacing the guessed size. If the build time exceeds the limit, log a blocker ([[edge-depth-table-stories]] Story E7).

**Effort:** M
**Priority:** P0
**Depends on:** `US-041` and `US-042`, both done. The limit is 5 minutes after the end of `3_calculate_depth`, never delaying the tile task, so it needs a live DAG run of task `9c`, which means the DAG unpaused. The unloaded numbers so far are 42.0 s, 1,085,487 bytes, and 160 of 160 values equal.

**Sprint:** 8, carried to the Backlog on 2026-10-05 because it needs the DAG unpaused for the 48-hour window. [[edge-depth-table-stories]] Story E7 (US-045), in [[sprint-plan-2]].

**Status note:** the timing report is built (`scripts/edge_depth/table_timing.ps1`, plan [[edge-depth-table-server-proof]]). It runs after the first runs of the window and again at the 24-hour and 48-hour readings.

### Active - US-069 Check the storage after the 48-hour replay to see if the retention fixes work

**What:** Read the free space on C:, the size of `docker_data.vhdx`, the three database sizes (`storage-postgres-data`, `minio_custom`, `netcdf_values`), and the `flood_extent_polygon` rows at the start, at 24 hours, and at 48 hours of the replay. The check passes if the database sizes stop growing between hour 24 and hour 48 ([[carried-over-backlog]] Story 12).

**Effort:** S
**Priority:** P1
**Depends on:** the DAG unpaused for 48 hours ([[carried-over-backlog]] Story 8, `US-063`). You parked it on 2026-10-05 and said to continue after Sprint 7. It can share the DAG run that `US-045` needs.

**Sprint:** 8, carried to the Backlog on 2026-10-05 because it needs the DAG unpaused for 48 hours. [[carried-over-backlog]] Story 12 (US-069), in [[sprint-plan-2]].

**Window:** the replay started at `2026-10-05T17:00:00Z` (00:00 +07 on 2026-10-06). Readings at 0 hours (before the unpause), 24 hours (00:00 +07 on 2026-10-07), and 48 hours (00:00 +07 on 2026-10-08).

**0-hour reading (21:32 +07, 2026-10-05):** C: free 153.6 GiB, `docker_data.vhdx` 107.48 GiB, `minio_custom` 14 GB, `flood_extent_polygon` 5,146 MB (112 rows, 8 runs), `netcdf_values` 320 MB (compressed 376 to 38 MB), `storage-postgres-data` 15.82 GB. No image builds on the server during the window.

**24-hour reading:** not recorded yet.

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
