# TODOS

## Current sprint: Sprint 5, 2026-10-01 to 2026-10-25

### Done - US-046 Record the routing baselines on the server

**What:** Write down the p50 and p95 of `POST /route` (flexible mode with LM) for a short, a medium, and a long Hanoi trip, the edge count of `hanoi-model-area.osm.pbf`, the source revision of the pinned GraphHopper image, and the step length and count of one real run ([[time-aware-routing-engine-stories]] Story R1).

**Effort:** S
**Priority:** P0
**Depends on:** None. The latency numbers waited for the `US-037` knob, which settled on 2026-10-02.

**Sprint:** 5, [[time-aware-routing-engine-stories]] Story R1 (US-046), in [[sprint-plan-2]].

**Result:** 2026-10-02, GraphHopper alone answers `POST /route` in 8 to 21 ms at the p50, and with the run's flood model in 153 to 1,857 ms. The graph has 67,833 edges and a run has 8 steps of 15 minutes.

### Active - US-034 Soak the flood-road backend and check it against known answers

**What:** Run the GraphHopper flood-road backend for 48 hours on the live app. The container logs must show no unexplained 5xx responses, and `POST /route` must block or allow each road of a fixed set according to the vehicle depth limits ([[carried-over-backlog]] Story 3).

**Effort:** M
**Priority:** P2
**Depends on:** [[carried-over-backlog]] Story 8 (`US-063`), for the rain the soak runs under.

**Sprint:** 5, [[carried-over-backlog]] Story 3 (US-034), in [[sprint-plan-2]].

**Today:** 2026-10-02, the first window (from 00:45 +07) is void. You stopped the pipeline, because the 50 mm/h rain is not a real event, and Docker on the server returned HTTP 500 at 13:53 +07. Docker works again, and every container was recreated at about 15:00 ([[2026-10-02-disk-cleanup-and-d-drive-move]]). The soak clock started with the replay at 2026-10-02 16:00 +07 and ends on 2026-10-04 at 16:00 +07. Your checks: `sh scripts/backend_soak/run_soak.sh 2026-10-02T16:00:00+07:00` once a day (expect exit code 0), and at the end after 16:00 +07 on 2026-10-04. `US-064` is done, so a failed read cannot pass.

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

### Active - US-068 Show the rain ingested into the simulation in the XCom of `1_trigger_simulation`

**What:** `1_trigger_simulation` pushes a `rain_ingested` XCom next to `sim_id`: the slot, the rain source, the interval count, the first and last offset, the maximum mm/h, and the total mm of the series sent to 3Di ([[carried-over-backlog]] Story 11).

**Effort:** S
**Priority:** P2
**Depends on:** None. It needs no server to build.

**Sprint:** 5, [[carried-over-backlog]] Story 11 (US-068), in [[sprint-plan-2]].

### Active - US-069 Check the storage after the 48-hour replay to see if the retention fixes work

**What:** Read the free space on C:, the size of `docker_data.vhdx`, the three database sizes (`storage-postgres-data`, `minio_custom`, `netcdf_values`), and the `flood_extent_polygon` rows at the start, at 24 hours, and at 48 hours of the replay. The check passes if the database sizes stop growing between hour 24 and hour 48 ([[carried-over-backlog]] Story 12).

**Effort:** S
**Priority:** P1
**Depends on:** [[carried-over-backlog]] Story 8 (`US-063`), the replay running again. The start time is still to be given.

**Sprint:** 5, [[carried-over-backlog]] Story 12 (US-069), in [[sprint-plan-2]].

## Backlog

Unfinished items carried over from Sprint 4:

### Active - US-037 Narrow the per-run critical path under the 15-minute cycle

**What:** Speed up the slowest steps of a run (trigger, `3_calculate_depth`, raster load, tile build) so every simulated run publishes step 1 before it becomes now, with a measured margin ([[carried-over-backlog]] Story 6, option D of [[five-minute-tile-freshness]]).

**Effort:** M
**Priority:** P2
**Depends on:** [[carried-over-backlog]] Story 8 (`US-063`), for the retest.

**Sprint:** 4, [[carried-over-backlog]] Story 6 (US-037), in [[sprint-plan]].

**Today:** 2026-10-05, still open. The `US-063` replay stopped early at 137 of the intended 192 runs (last one 2026-10-03 19:00 UTC, an unrelated stale run ended during today's disk incident), and nobody has run `scripts/pipeline_margins/report.py`, this story's own pass check, against the window yet. A critical-path analysis of the 136 completed runs stayed under the 15-minute budget throughout, but `9_build_flood_tiles` alone grew 4.8x over the 48 hours with no cross-run overlap to explain it; an unverified lead points at `flood_extent_polygon`'s unbounded growth over the same window. Not closing until the official report runs and that lead is checked. Details in [[us-037-narrow-the-per-run-critical-path]].

## Blockers for the next sprint

The next sprint is Sprint 6, 2026-10-26 to 2026-11-01. 

Checked on 2026-10-02 against its rows (`US-049`, `US-039`).

Any blocker stops Sprint 6: None

The unresolved blockers are:

1. [[route-panel-stuck-on-loading-bars]]
2. [[map-shows-forecast-not-now]]
3. [[routing-not-time-aware]]
4. [[place-name-slow-after-map-tap]], which blocks no build. Its story `US-061` has no sprint.
