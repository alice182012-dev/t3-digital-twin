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

### Active - US-063 Replay a realistic 48-hour rain for the `US-037` retest and the `US-034` soak

**What:** Replace the constant 50 mm/h test rain with the Hanoi rain of 2025-10-05 to 2025-10-08, cut to 48 hours (2025-10-05T22:30Z to 2025-10-07T22:30Z, 246.8 mm, peak 56.48 mm/h). The server's gate is 0.01 mm/h, so all 192 runs simulate. At 5 mm/h, 104 would simulate ([[carried-over-backlog]] Story 8, plan in [[us-063-realistic-rain-replay-for-us-037-and-us-034]]).

**Effort:** S
**Priority:** P2
**Depends on:** None. The server steps wait for your go. Docker works again ([[2026-10-02-disk-cleanup-and-d-drive-move]]).

**Sprint:** 5, [[carried-over-backlog]] Story 8 (US-063), in [[sprint-plan-2]].

**Today:** 2026-10-02, running. The server got `c3d398e` at 15:20 +07, and you unpaused `flood_mapping_full` at about 15:54 +07. The 16:00 slot read the replay (`Replaying ... from 2026-10-02T09:00:00Z`, gate max 1.10 mm/h) and its simulation started. The 15:45 slot ran before that as a pre-roll. The window is one chain of 192 runs to 2026-10-04 15:45 +07. Your checks, with commands in the plan under "Checks while the replay runs": the peak check on 2026-10-03 after 16:35 +07 (expect `max=56.48 mm/h`), then the end of the window after 16:00 +07 on 2026-10-04.

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

## Backlog

Unfinished items carried over from Sprint 4:

### Active - US-037 Narrow the per-run critical path under the 15-minute cycle

**What:** Speed up the slowest steps of a run (trigger, `3_calculate_depth`, raster load, tile build) so every simulated run publishes step 1 before it becomes now, with a measured margin ([[carried-over-backlog]] Story 6, option D of [[five-minute-tile-freshness]]).

**Effort:** M
**Priority:** P2
**Depends on:** [[carried-over-backlog]] Story 8 (`US-063`), for the retest.

**Sprint:** 4, [[carried-over-backlog]] Story 6 (US-037), in [[sprint-plan]].

**Today:** 2026-10-02, reopened. Four runs published step 1 with margins of +1.9 to +4.1 minutes, but under a constant 50 mm/h rain that you judged unrealistic. The margin shrank about 0.6 minutes per run. Your checks: the run report of `US-065` every few hours (late and missing runs), and at the end with `--until "10-04 15:45"`. The retest runs the 48-hour replay of `US-063`. The report on the old storm shows the margin was +2.3 minutes in the 01:00 hour and -0.7 or lower from 03:00. It waits for the server.

## Blockers for the next sprint

The next sprint is Sprint 6, 2026-10-26 to 2026-11-01. 

Checked on 2026-10-02 against its rows (`US-049`, `US-039`).

Any blocker stops Sprint 6: None

The unresolved blockers are:

1. [[route-panel-stuck-on-loading-bars]]
2. [[map-shows-forecast-not-now]]
3. [[routing-not-time-aware]]
4. [[place-name-slow-after-map-tap]], which blocks no build. Its story `US-061` has no sprint.
