---
date_drafted: 2026-09-29
type: user-story
us_id: "US-050"
story_label: "R5"
epic: "[[EP-09-time-aware-routing-engine]]"
status: Done
priority: P0
estimate: L
sprint: 8
subsystem: floodmap-backend, floodmap-frontend
related: ["[[EP-09-time-aware-routing-engine]]", "[[SP-02-routing-engine-foundations|sprint-plan-2]]"]
title: "Build the time-aware weighting and search for `motorbike` and `car`"
---

# US-050 Build the time-aware weighting and search for `motorbike` and `car`

As a traveller, I want the route to account for the time I reach each road, so I am not sent into water that
floods before I arrive.
Given a synthetic depth table in the format of [[EP-08-edge-depth-table|edge-depth-table-stories]] Story E2, when the four
scenarios run for `motorbike` and `car`, with and without a detour, then the results match the reference
from Story R2 and the checker finds no crossing of an impassable edge. The search carries the arrival time
in its label, applies sticky closure from the departure step with a 10-minute margin, and reads the vehicle
limit from the profile.
Priority: P0. Status: Done. Estimate: L. Sprint: 8. Dependencies: Stories R2, R4, E2. Gate cleared: the user
confirmed the sticky-from-departure wording on 2026-10-02.
Evidence: ![[us-050-scenario-check-server-output.png]]
Details:
1. What: the time-aware weighting and search of the sticky C-lite engine in `java/time-aware-routing/`: `StickyClosure` (the closure rule), `TimeAwareDijkstra` (labels of weight and time), `StickyChecker`, `TimeAwareRouter` (hooks into GraphHopper's `route()`), and `ScenarioReport` with `scenario-check.sh`.
2. How: tests first, 41 new module tests (98 in all). A road is closed for an arrival when a step in `[departure, arrival + 10 min]` has a depth at or above the limit, and steps before the departure are ignored. The search keeps several labels per node and drops one only when another is no heavier and no later, so it stays exact when weight and time differ. A request with the hint `td_departure` on a profile with `td_limit_cm` gets this search, and every other request goes the stock way. A snap in the middle of a road is mapped to the road's edge id (`VirtualEdgeIterator` is not a `VirtualEdgeIteratorState`, so the search detaches the edge). A random-graph test against an exhaustive search passes. Five changes each fail a test: no dominance rule, never closing, no virtual-edge mapping, a fixed limit, and an excluded window end.
3. Why: a road that is dry at the request step and floods before the traveller arrives is a safety fault in today's single-step routing, and GraphHopper's weighting has no arrival time, so the search has to carry it.
4. Effect: on the server, the image build ran all module tests and then `ScenarioReport` ran the 4 scenarios for motorbike and car, with and without a detour. All 16 runs match the sticky column of the blocker's test table with 0 crossings, and the plain shortest route crosses the closed road in all 8 blocked runs. `US-051` can add `truck` and `foot` as profiles with `td_limit_cm`. `US-052` connects `LatestTableSource` through `setTableSupplier`, adds the server flag, the request clock, and the fallback flag. `US-055` measures latency.
5. Limits: the scenarios run on a hand-built corridor with exact minutes, not on real Hanoi roads (`US-055`). No server request is time-aware yet, because nothing sets the table supplier or the departure hint. The search skips landmarks and contraction hierarchies, so it visits more nodes than today's search, and the latency is not measured. Turn costs are handled in the code and are not tested. The evidence image is rendered from output the user pasted.
