# TODOS

## Current sprint: Sprint 5, 2026-10-01 to 2026-10-25

### Done - US-040 Define the table format and write the Python reader and writer

**What:** One documented file format for a run's depth by edge id, with a reference reader and writer, so the Java engine and the Python timeline read the same bytes ([[edge-depth-table-stories]] Story E2, format in [[edge-depth-table-format]]).

**Effort:** S
**Priority:** P0
**Depends on:** None.

**Sprint:** 5, [[edge-depth-table-stories]] Story E2 (US-040), in [[sprint-plan-2]].

**Result:** 2026-10-01, the reader and writer pass 25 tests, and a table of 2,000,000 edges and 9 steps is 36.0 MB.

### Done - US-047 Build the synthetic scenarios, the offline reference, and the offline checker

**What:** A slow time-dependent Dijkstra reference and a route checker, run on a synthetic flood over a real Hanoi corridor (code in `scripts/routing_reference/`), so the fast engine has something to be compared against ([[time-aware-routing-engine-stories]] Story R2).

**Effort:** M
**Priority:** P0
**Depends on:** None.

**Sprint:** 5, [[time-aware-routing-engine-stories]] Story R2 (US-047), in [[sprint-plan-2]].

**Result:** 2026-10-01, the reference and checker pass 54 tests, and all 16 scenario runs on real Hanoi roads match the sticky column with no crossing.

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
**Depends on:** None. The `US-037` knob settled on 2026-10-02, and the soak clock started at 00:45 +07 under one worker configuration.

**Sprint:** 5, [[carried-over-backlog]] Story 3 (US-034), in [[sprint-plan-2]].

**Today:** 2026-10-02, the soak runs from 00:45 +07 and ends on 2026-10-04 at 00:45 +07. After 2 hours 28 minutes the logs show no 5xx response and no error line, and the known-answer check passed 86 of 92 pairs and skipped 6. Run `sh scripts/backend_soak/run_soak.sh` after the window ends.

### Active - US-062 Find out how fast a user must react to the flood map

**What:** Research the shortest time in which a person must act on what the map shows, for each kind of user, and decide whether the 15-minute refresh is enough ([[map-refresh-requirement-research]], plan in [[map-refresh-requirement-research-plan]]). The research is done ([[flood-map-reaction-time-findings]]). It waits for your decision on the refresh interval.

**Effort:** M
**Priority:** P2
**Depends on:** Your decision on the refresh interval.

**Sprint:** 5, [[map-refresh-requirement-research]] (US-062), in [[sprint-plan-2]].

## Backlog

Unfinished items carried over from Sprint 4:

### Done - US-037 Narrow the per-run critical path under the 15-minute cycle

**What:** Speed up the slowest steps of a run (trigger, `3_calculate_depth`, raster load, tile build) so four consecutive real runs publish step 1 before it becomes now, with a measured margin ([[carried-over-backlog]] Story 6, option D of [[five-minute-tile-freshness]]).

**Effort:** M
**Priority:** P2
**Depends on:** None.

**Sprint:** 4, [[carried-over-backlog]] Story 6 (US-037), in [[sprint-plan]].

**Result:** 2026-10-02, four consecutive on-time runs published step 1 with margins of +1.9, +4.1, +2.7, and +2.4 minutes. The margin shrinks about 0.6 minutes per run as the test storm grows.

## Blockers for the next sprint

The next sprint is Sprint 6, 2026-10-26 to 2026-11-01. 

Checked on 2026-10-01 against its rows (`US-049`, `US-039`).

Any blocker stops Sprint 6: None

The unresolved blockers are:

1. [[route-panel-stuck-on-loading-bars]]
2. [[map-shows-forecast-not-now]]
3. [[routing-not-time-aware]]
