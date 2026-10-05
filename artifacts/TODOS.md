# TODOS

## Current sprint: Sprint 6, 2026-10-05 to 2026-11-01

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

### Active - US-049 Build the Java module skeleton, the image, and the CI job

**What:** A Java module built against the pinned GraphHopper version (commit `d7dc1b06`), an image that runs it in place of the stock class, and a GitHub Actions job that builds and tests it ([[time-aware-routing-engine-stories]] Story R4, plan in [[sprint-6-java-toolchain-and-edge-export]]).

**Effort:** L
**Priority:** P0
**Depends on:** [[time-aware-routing-engine-stories]] Story R1 (`US-046`), which is done. The server is free, since you paused `flood_mapping_full` on 2026-10-05.

**Sprint:** 6, [[time-aware-routing-engine-stories]] Story R4 (US-049), in [[sprint-plan-2]].

**Today:** 2026-10-05, built and tested on the Mac side (9 tests pass, LM stays valid for a raise-only weighting). CI run 1 passed on 2026-10-05 (commit `ef5ef4c`, [run](https://github.com/alice182012-dev/t3-digital-twin/actions/runs/37267377140)). Left: `docker --context remote-server build --target test java/time-aware-routing` and an image start on the server, then a screenshot of both. The server is free, since you paused the DAG.

### Active - US-039 Export the graph's edges

**What:** Export every edge of the GraphHopper graph with its id and geometry, plus the graph's hash, as `edges.csv` and `graph.json` ([[edge-depth-table-stories]] Story E1, plan in [[sprint-6-java-toolchain-and-edge-export]]).

**Effort:** M
**Priority:** P0
**Depends on:** `US-049`, same sprint.

**Sprint:** 6, [[edge-depth-table-stories]] Story E1 (US-039), in [[sprint-plan-2]].

**Today:** 2026-10-05, not started. It waits for the module of `US-049`. Tests on a tiny OSM file come first, then the run on the server with the graph cache read-only (expect 67,833 rows).

## Backlog

Unfinished items carried over from Sprint 5 and Sprint 4:

### Done - US-037 Narrow the per-run critical path under the 15-minute cycle

**What:** Speed up the slowest steps of a run (trigger, `3_calculate_depth`, raster load, tile build) so every simulated run publishes step 1 before it becomes now, with a measured margin ([[carried-over-backlog]] Story 6, option D of [[five-minute-tile-freshness]]).

**Effort:** M
**Priority:** P2
**Depends on:** [[carried-over-backlog]] Story 8 (`US-063`), for the retest.

**Sprint:** 4, [[carried-over-backlog]] Story 6 (US-037), in [[sprint-plan]].

**Result:** 2026-10-05, closed again on the 137 runs, at your decision. The 136 completed runs stayed under the 15-minute budget (maximum 14.9 minutes), but `report.py` was not run and `9_build_flood_tiles` grew 4.8 times over the window. The `flood_extent_polygon` lead (now pruned by `US-067`) is not verified. Details in [[us-037-narrow-the-per-run-critical-path]].

### Active - US-068 Show the rain ingested into the simulation in the XCom of `1_trigger_simulation`

**What:** `1_trigger_simulation` pushes a `rain_ingested` XCom next to `sim_id`: the slot, the rain source, the interval count, the first and last offset, the maximum mm/h, and the total mm of the series sent to 3Di ([[carried-over-backlog]] Story 11).

**Effort:** S
**Priority:** P2
**Depends on:** None. It needs no server to build.

**Sprint:** 5, [[carried-over-backlog]] Story 11 (US-068), in [[sprint-plan-2]].

**Today:** 2026-10-05, built and tested: `rain_ingested` is pushed from `1_trigger_simulation` (22 tests pass). The real XCom check needs one DAG run, so it waits for you to unpause the DAG and pull the commit on the server.

## Blockers for the next sprint

The next sprint is Sprint 7, 2026-11-02 to 2026-11-08.

Checked on 2026-10-05 against its rows (`US-041`, `US-042`, `US-044`).

Any blocker stops Sprint 7: None

The unresolved blockers are:

1. [[route-panel-stuck-on-loading-bars]]
2. [[map-shows-forecast-not-now]]
3. [[routing-not-time-aware]]
4. [[place-name-slow-after-map-tap]], which blocks no build. Its story `US-061` has no sprint.
