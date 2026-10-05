# TODOS

## Current sprint: Sprint 10, 2026-10-05 to 2026-11-29

### Done - US-046 Record the routing baselines on the server

**What:** Write down the p50 and p95 of `POST /route` (flexible mode with LM) for a short, a medium, and a long Hanoi trip, the edge count of `hanoi-model-area.osm.pbf`, the source revision of the pinned GraphHopper image, and the step length and count of one real run ([[time-aware-routing-engine-stories]] Story R1).

**Effort:** S
**Priority:** P0
**Depends on:** None. The latency numbers waited for the `US-037` knob, which settled on 2026-10-02.

**Sprint:** 5, [[time-aware-routing-engine-stories]] Story R1 (US-046), in [[sprint-plan-2]].

**Result:** 2026-10-02, GraphHopper alone answers `POST /route` in 8 to 21 ms at the p50, and with the run's flood model in 153 to 1,857 ms. The graph has 67,833 edges and a run has 8 steps of 15 minutes.

### Done - US-034 Soak the flood-road backend and check it against known answers

**What:** Run the GraphHopper flood-road backend for 48 hours on the live app. The container logs must show no unexplained 5xx responses, and `POST /route` must block or allow each road of a fixed set according to the vehicle depth limits ([[carried-over-backlog]] Story 3).

**Effort:** M
**Priority:** P2
**Depends on:** [[carried-over-backlog]] Story 8 (`US-063`), for the rain the soak runs under.

**Sprint:** 5, [[carried-over-backlog]] Story 3 (US-034), in [[sprint-plan-2]].

**Result:** 2026-10-05, closed on the 137 runs of the replay that ran, at your decision, so Sprint 6 can start. The end check of `run_soak.sh` was not run and the evidence is waived. The first run on the real host (2026-10-02) passed the container and known-answer checks (14 roads, 56 checks).

### Done - US-063 Replay a realistic 48-hour rain for the `US-037` retest and the `US-034` soak

**What:** Replace the constant 50 mm/h test rain with the Hanoi rain of 2025-10-05 to 2025-10-08, cut to 48 hours (2025-10-05T22:30Z to 2025-10-07T22:30Z, 246.8 mm, peak 56.48 mm/h). The server's gate is 0.01 mm/h, so all 192 runs simulate. At 5 mm/h, 104 would simulate ([[carried-over-backlog]] Story 8, plan in [[us-063-realistic-rain-replay-for-us-037-and-us-034]]).

**Effort:** S
**Priority:** P2
**Depends on:** None. The server steps wait for your go. Docker works again ([[2026-10-02-disk-cleanup-and-d-drive-move]]).

**Sprint:** 5, [[carried-over-backlog]] Story 8 (US-063), in [[sprint-plan-2]].

**Result:** 2026-10-05, 137 of the 192 runs completed (136 success, 1 failed) before the 2026-10-04 disk-full incident cut the chain short. The `Replaying` line and the peak rate (`max=56.48 mm/h`) both match real server logs. `US-037` and `US-034` need the fuller window and stay open.

### Done - US-064 Make the soak check fail when it cannot read the server

**What:** `run_soak.sh` must exit with 1 when a Docker call or a log read fails. On 2026-10-02 at 13:53 +07 it printed "logs exit 0" while Docker answered HTTP 500 on every call ([[carried-over-backlog]] Story 9).

**Effort:** S
**Priority:** P1
**Depends on:** None. It needs no server.

**Sprint:** 5, [[carried-over-backlog]] Story 9 (US-064), in [[sprint-plan-2]].

**Result:** 2026-10-02, `run_soak.sh` exits with 1 when a Docker call fails, a log has no timestamped line, or a container started inside the window. 42 tests pass, and a replay of the 13:53 outage exits with 1.

### Done - US-065 Report the step-1 margin of every run of the replay

**What:** One command that reads the per-run timings of the 48-hour replay and exits with 0 only if every simulated run published step 1 before it became now and none is missing ([[carried-over-backlog]] Story 10).

**Effort:** M
**Priority:** P2
**Depends on:** `US-063`, for the schedule preview. It needs no server to build.

**Sprint:** 5, [[carried-over-backlog]] Story 10 (US-065), in [[sprint-plan-2]].

**Result:** 2026-10-02, the report passes 21 tests. Run on 50 real runs of the 50 mm/h storm it fails: the mean margin was +2.3 minutes in the 01:00 hour and -0.7 or lower from 03:00, as the tile task grew from 5.8 to 11.5 minutes.

### Done - US-062 Find out how fast a user must react to the flood map

**What:** Research the shortest time in which a person must act on what the map shows, for each kind of user, and decide whether the 15-minute refresh is enough ([[map-refresh-requirement-research]], plan in [[map-refresh-requirement-research-plan]]). The research is done ([[flood-map-reaction-time-findings]]), and you decided to keep 15 minutes.

**Effort:** M
**Priority:** P2
**Depends on:** None.

**Sprint:** 5, [[map-refresh-requirement-research]] (US-062), in [[sprint-plan-2]].

**Result:** 2026-10-02, you decided to keep the 15-minute refresh for now. The map-age label and a faster pipeline were not chosen.

### Done - US-066 Narrow and compress netcdf_values onto TimescaleDB

**What:** Redesign `netcdf_values` into a narrow, compressed, retention-managed TimescaleDB hypertable, so the mesh-simulation ingest pipeline stops refilling C: every time a long soak test runs ([[netcdf-values-storage-redesign]], plan in [[netcdf-values-timescale-migration]]).

**Effort:** L
**Priority:** P1
**Depends on:** None.

**Sprint:** 5, [[netcdf-values-storage-redesign]] (US-066), in [[sprint-plan-2]].

**Result:** 2026-10-05, criteria 1 to 3 re-verified live against the real containers and recorded with rendered evidence. Criterion 4 spot-check found only 2 of 112 old file_ids were ever backfilled, both matching row for row; the other 110 are pre-migration soak data nothing in the codebase reads. Dropped on the user's go: `DROP TABLE netcdf_values;` ran clean, `minio_custom` went from 70 GB to 14 GB ([[2026-10-05-us-066-criterion-4-spot-check]]).

### Done - US-067 Prune old runs' flood_extent_polygon rows on every publish

**What:** Add `prune_polygon_rows` to `scripts/flood_extent/publish.py`, called from `publish_run` right after `prune_step_rows`, deleting `flood_extent_polygon` rows for every run outside the newest `keep_runs` ([[prune-flood-extent-polygon-rows]]).

**Effort:** S
**Priority:** P1
**Depends on:** None.

**Sprint:** 5, [[prune-flood-extent-polygon-rows]] (US-067), in [[sprint-plan-2]].

**Result:** 2026-10-05, 21 tests pass against a throwaway PostGIS container. `flood_extent_polygon` had no retention policy and reached 13 GB by 2026-10-04 ([[docker-data-vhdx-fills-c-drive-again]]); it now gets the same automated per-publish prune `flood_extent_step` and the MinIO bucket already had.

### Done - US-049 Build the Java module skeleton, the image, and the CI job

**What:** A Java module built against the pinned GraphHopper version (commit `d7dc1b06`), an image that runs it in place of the stock class, and a GitHub Actions job that builds and tests it ([[time-aware-routing-engine-stories]] Story R4, plan in [[sprint-6-java-toolchain-and-edge-export]]).

**Effort:** L
**Priority:** P0
**Depends on:** [[time-aware-routing-engine-stories]] Story R1 (`US-046`), which is done. The server is free, since you paused `flood_mapping_full` on 2026-10-05.

**Sprint:** 6, [[time-aware-routing-engine-stories]] Story R4 (US-049), in [[sprint-plan-2]].

**Result:** 2026-10-05, CI run 1 passed, and the image started on the server beside the live GraphHopper with `TimeAwareGraphHopper active` in its log. 12 of 12 routes matched the live service. LM stays valid for a raise-only weighting. The test container is still running on port 8990 until you run `java/time-aware-routing/smoke-test.sh cleanup`.

### Done - US-039 Export the graph's edges

**What:** Export every edge of the GraphHopper graph with its id and geometry, plus the graph's hash, as `edges.csv` and `graph.json` ([[edge-depth-table-stories]] Story E1, plan in [[sprint-6-java-toolchain-and-edge-export]]).

**Effort:** M
**Priority:** P0
**Depends on:** `US-049`, same sprint.

**Sprint:** 6, [[edge-depth-table-stories]] Story E1 (US-039), in [[sprint-plan-2]].

**Result:** 2026-10-05, the export ran on the live graph on the server, read-only: 67,833 rows for 67,833 edges, identical on two runs, one hash (`8c13d884...c716ce`). A first run failed on the read-only mount and was fixed.

### Done - US-041 Build the Airflow task that writes each run's table

**What:** An Airflow task after `9b_load_depth_raster` samples the raster tiles along each edge of the export, stores the deepest 1 m sample in centimetres, tags the file with the graph hash, and reports its duration and size. For 20 hand-picked edges the values equal a direct `ST_Value` reading, and an edge outside the model reads 0 ([[edge-depth-table-stories]] Story E3).

**Effort:** L
**Priority:** P0
**Depends on:** `US-039` (the export) and `US-040` (the format), both done. The table task must run beside the tile task and end within 5 minutes of `3_calculate_depth`, never delaying the tile task.

**Sprint:** 7, [[edge-depth-table-stories]] Story E3 (US-041), in [[sprint-plan-2]].

**Result:** 2026-10-05, on the server the table for run `20261005T120000` has 67,833 edges by 8 steps (1,085,487 bytes), built in 42.0 s with no other load, and all 160 values of a 20-edge spot check equal a direct `ST_Value` reading. Built through the Airflow worker, not a DAG run, because the DAG is paused.

### Done - US-042 Publish the table atomically and keep the newest three runs

**What:** A new table appears in one step, so a reader never sees a half-written file. The fourth run's publish removes the oldest, and a failed task leaves the previous `latest` in place. The story also picks the storage, a volume or MinIO, and records why ([[edge-depth-table-stories]] Story E4).

**Effort:** S
**Priority:** P0
**Depends on:** `US-041`, same sprint.

**Sprint:** 7, [[edge-depth-table-stories]] Story E4 (US-042), in [[sprint-plan-2]].

**Result:** 2026-10-05, on the server a reader in its own process made 11,878 reads while 41 tables published into a scratch folder on the new volume `edge-depth-tables`: none failed, and 3 tables were left. The real table for run `20261005T120000` is published and `latest` names it.

### Done - US-044 Document the graph re-import procedure and detect a stale table

**What:** A concept page that says what to do after a graph re-import, so the export, the table, and the hash are regenerated together. A reader refuses a table whose hash differs from the graph's, and the log names the mismatch ([[edge-depth-table-stories]] Story E6).

**Effort:** S
**Priority:** P1
**Depends on:** `US-041`, same sprint.

**Sprint:** 7, [[edge-depth-table-stories]] Story E6 (US-044), in [[sprint-plan-2]].

**Result:** 2026-10-05, on the server the check says `FRESH` when the export, `graph_edge`, and the `latest` table share hash `8c13d884...`, and `STALE` against another hash, naming both and exiting 1. The page [[graph-reimport-procedure]] and a Python guard are in. You confirmed that the refusal at request time is `US-043`'s.

### Done - US-043 Build the Java reader with a hash check and reload without restart

**What:** A Java reader of the edge depth table, in `java/time-aware-routing/`. It returns the same values as the Python reader for every edge and step on the shared fixture, refuses a table for a different graph hash and names both hashes, and memory-maps a new `latest` within 30 seconds while a request in flight finishes on the old table ([[edge-depth-table-stories]] Story E5). This is where the request-time refusal that `US-044` handed over is built.

**Effort:** M
**Priority:** P0
**Depends on:** `US-040` (the format) and `US-049` (the module), both done. The tables are on the volume `edge-depth-tables`, and the Python guard in `edge_depth_table.py` gives the wording of the refusal.

**Sprint:** 8, [[edge-depth-table-stories]] Story E5 (US-043), in [[sprint-plan-2]].

**Result:** 2026-10-05, on the server a second container read the real table (67,833 edges, 8 steps) against the live graph hash `8c13d884...`, refused another hash naming both and exiting 1, and loaded a new `latest` 8 s after the worker published it, with no restart.

### Done - US-050 Build the time-aware weighting and search for `motorbike` and `car`

**What:** A weighting and a search that carry the arrival time in the label, apply sticky closure from the departure step with a 10-minute margin, and read the vehicle limit from the profile. On a synthetic depth table the four scenarios, with and without a detour, must match the reference of `US-047`, and the checker must find no crossing of an impassable edge ([[time-aware-routing-engine-stories]] Story R5).

**Effort:** L
**Priority:** P0
**Depends on:** `US-047` (the reference), `US-049` (the module, and the answer that landmarks stay valid for a raise-only weighting), and `US-040` (the format), all done. The sticky-from-departure wording was confirmed on 2026-10-02.

**Sprint:** 8, [[time-aware-routing-engine-stories]] Story R5 (US-050), in [[sprint-plan-2]].

**Result:** 2026-10-05, on the server all 16 runs (4 scenarios, motorbike and car, with and without a detour) match the sticky column with 0 crossings, and the plain route crosses the closed road in all 8 blocked runs.

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

## Backlog

Unfinished items carried over from Sprint 8 and Sprint 4. The Done items of Sprints 5 to 8 above stay until the next rollover, then they are deleted.

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

**Window:** the replay is set to start at `2026-10-05T17:00:00Z` (00:00 +07 on 2026-10-06). It was moved from 22:15 +07 because that slot passed before the unpause. Readings at 0 hours (before the unpause), 24 hours (00:00 +07 on 2026-10-07), and 48 hours (00:00 +07 on 2026-10-08). The DAG is still paused until you unpause it.

**0-hour reading (21:32 +07, 2026-10-05):** C: free 153.6 GiB, `docker_data.vhdx` 107.48 GiB, `minio_custom` 14 GB, `flood_extent_polygon` 5,146 MB (112 rows, 8 runs), `netcdf_values` 320 MB (compressed 376 to 38 MB), `storage-postgres-data` 15.82 GB. No image builds on the server during the window.


### Done - US-037 Narrow the per-run critical path under the 15-minute cycle

**What:** Speed up the slowest steps of a run (trigger, `3_calculate_depth`, raster load, tile build) so every simulated run publishes step 1 before it becomes now, with a measured margin ([[carried-over-backlog]] Story 6, option D of [[five-minute-tile-freshness]]).

**Effort:** M
**Priority:** P2
**Depends on:** [[carried-over-backlog]] Story 8 (`US-063`), for the retest.

**Sprint:** 4, [[carried-over-backlog]] Story 6 (US-037), in [[sprint-plan]].

**Result:** 2026-10-05, closed again on the 137 runs, at your decision. The 136 completed runs stayed under the 15-minute budget (maximum 14.9 minutes), but `report.py` was not run and `9_build_flood_tiles` grew 4.8 times over the window. The `flood_extent_polygon` lead (now pruned by `US-067`) is not verified. Details in [[us-037-narrow-the-per-run-critical-path]].

### Done - US-068 Show the rain ingested into the simulation in the XCom of `1_trigger_simulation`

**What:** `1_trigger_simulation` pushes a `rain_ingested` XCom next to `sim_id`: the slot, the rain source, the interval count, the first and last offset, the maximum mm/h, and the total mm of the series sent to 3Di ([[carried-over-backlog]] Story 11).

**Effort:** S
**Priority:** P2
**Depends on:** None. It needs no server to build.

**Sprint:** 5, [[carried-over-backlog]] Story 11 (US-068), in [[sprint-plan-2]].

**Result:** 2026-10-05, on the server the first run of the replay (slot `2026-10-05T17:00Z`) pushed `rain_ingested`: source `replay:hanoi_20251005_48h.csv`, 9 points from 0 to 7200 s, 1.096 mm/h at most, 0.881 mm in total. The same numbers come out of the event file.

## Blockers for the next sprint

The next sprint is Sprint 11, 2026-11-30 to 2026-12-06, in [[sprint-plan-3]].

Checked on 2026-10-05 against its row (`US-033`).

Any blocker stops Sprint 11: None

The unresolved blockers are:

1. [[route-panel-stuck-on-loading-bars]], monitoring.
2. [[map-shows-forecast-not-now]], monitoring.
3. [[routing-not-time-aware]], which `US-055` resolves.
4. [[place-name-slow-after-map-tap]], which blocks no build. Its story `US-061` has no sprint.
