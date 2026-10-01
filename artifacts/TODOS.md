# TODOS

## Current sprint: Sprint 4, 2026-10-01 to 2026-10-18

### Done - US-060 Run the flood metric extractor on a retained run

**What:** Run `scripts/flood_metrics/extract_run.py` on a retained run, for example 2026-09-30 02:00:00, and compare the stored rows with `flood_road_values` ([[timescaledb-and-flood-metrics]] Story 5). The segment count must equal the run's distinct `geom_4326` values, and three hand-picked `peak_depth_m` values must equal the largest `depth` of their segment.

**Effort:** XS
**Priority:** P1
**Depends on:** US-020 (built), US-019 (done).

**Sprint:** 4, [[timescaledb-and-flood-metrics]] Story 5 (US-060), in [[sprint-plan]].

**Result:** 2026-10-01, 5,831 segments stored for the 2026-09-30 02:00:00 run, equal to its distinct `geom_4326` values, and `peak_depth_m` matches `flood_road_values` for all of them.

### Done - US-020 Build the flood metric extractor

**What:** The extractor is built and Reviewed. It moves to Done with the evidence of US-060 ([[timescaledb-and-flood-metrics]] Story 3).

**Effort:** L
**Priority:** P1
**Depends on:** US-060 (done).

**Sprint:** 4, [[timescaledb-and-flood-metrics]] Story 3 (US-020), in [[sprint-plan]].

**Result:** 2026-10-01, `Done` with the evidence of US-060.

### Active - US-037 Narrow the per-run critical path under the 15-minute cycle

**What:** Speed up the slowest steps of a run (trigger, `3_calculate_depth`, raster load, tile build) so four consecutive real runs publish step 1 before it becomes now, with a measured margin ([[carried-over-backlog]] Story 6, option D of [[five-minute-tile-freshness]]).

**Effort:** M
**Priority:** P2
**Depends on:** None.

**Sprint:** 4, [[carried-over-backlog]] Story 6 (US-037), in [[sprint-plan]].

### Done - US-032 Make the map toggle, legend, and route tabs usable by keyboard and screen reader

**What:** The Map or Flood toggle has `aria-pressed` and responds to Enter and Space. The route tabs have `role="tablist"` and `role="tab"` with `aria-selected` and move with the arrow keys. Every control has a touch target of at least 44 px, and the legend text has a contrast ratio of at least 4.5:1 ([[carried-over-backlog]] Story 1).

**Effort:** S
**Priority:** P2
**Depends on:** US-025, US-026, and US-059 (done).

**Sprint:** 4, [[carried-over-backlog]] Story 1 (US-032), in [[sprint-plan]].

**Result:** 2026-10-01, deployed and checked live: the route tabs move with the arrow keys and are 44 px tall, and the legend labels have an explicit color.

### Done - US-035 Revalidate "loading is very slow"

**What:** Measure the time to the first map and to the flood layer on the live app, and the routing panel's wait for a no-connection pair (9 seconds or more on 2026-09-30, [[route-panel-stuck-on-loading-bars]]). Close the item or open a blocker with the measured cause ([[carried-over-backlog]] Story 4).

**Effort:** S
**Priority:** P3
**Depends on:** US-032 (done).

**Sprint:** 4, [[carried-over-backlog]] Story 4 (US-035), in [[sprint-plan]].

**Result:** 2026-10-01, no slow load found: first map in 0.7 to 1.5 s and flood layer in 2.0 to 3.2 s, and the no-connection box in 1.5 to 2.6 s. The 9 to 20 s wait did not reproduce.

## Backlog

Unfinished items carried over from Sprint 3: None

## Blockers for the next sprint

The next sprint is Sprint 5, 2026-10-19 to 2026-10-25. Checked on 2026-10-01 against its rows (`US-046`, `US-047`, `US-040`, `US-034`).

Sprint 4 is not finished. `US-037` is the one open item, and no row of Sprint 5 depends on it. Sprint 5 starts when `US-037` is `Done`, or when the user moves it to the Backlog.

Any blocker stops Sprint 5: None

The unresolved blockers are:

1. [[route-panel-stuck-on-loading-bars]]
2. [[map-shows-forecast-not-now]]
3. [[routing-not-time-aware]]
