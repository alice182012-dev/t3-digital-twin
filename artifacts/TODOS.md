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

### Active - US-046 Record the routing baselines on the server

**What:** Write down the p50 and p95 of `POST /route` (flexible mode with LM) for a short, a medium, and a long Hanoi trip, the edge count of `hanoi-model-area.osm.pbf`, the source revision of the pinned GraphHopper image, and the step length and count of one real run ([[time-aware-routing-engine-stories]] Story R1).

**Effort:** S
**Priority:** P0
**Depends on:** None. The latency numbers wait for the `US-037` knob to settle, because the pipeline shares the server.

**Sprint:** 5, [[time-aware-routing-engine-stories]] Story R1 (US-046), in [[sprint-plan-2]].

### Active - US-034 Soak the flood-road backend and check it against known answers

**What:** Run the GraphHopper flood-road backend for 48 hours on the live app. The container logs must show no unexplained 5xx responses, and `POST /route` must block or allow each road of a fixed set according to the vehicle depth limits ([[carried-over-backlog]] Story 3).

**Effort:** M
**Priority:** P2
**Depends on:** None. Start the 48-hour clock after the `US-037` knob settles, so the soak runs under one worker configuration.

**Sprint:** 5, [[carried-over-backlog]] Story 3 (US-034), in [[sprint-plan-2]].

## Backlog

Unfinished items carried over from Sprint 4:

### Active - US-037 Narrow the per-run critical path under the 15-minute cycle

**What:** Speed up the slowest steps of a run (trigger, `3_calculate_depth`, raster load, tile build) so four consecutive real runs publish step 1 before it becomes now, with a measured margin ([[carried-over-backlog]] Story 6, option D of [[five-minute-tile-freshness]]).

**Effort:** M
**Priority:** P2
**Depends on:** None.

**Sprint:** 4, [[carried-over-backlog]] Story 6 (US-037), in [[sprint-plan]].

## Blockers for the next sprint

The next sprint is Sprint 6, 2026-10-26 to 2026-11-01. Checked on 2026-10-01 against its rows (`US-049`, `US-039`).

Any blocker stops Sprint 6: None

The unresolved blockers are:

1. [[route-panel-stuck-on-loading-bars]]
2. [[map-shows-forecast-not-now]]
3. [[routing-not-time-aware]]
