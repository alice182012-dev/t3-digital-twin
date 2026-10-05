---
date: 2026-10-05
type: plan
branch: front-end-according-to-mock-up
status: done
tags: [plan, sprint-8, java, routing, graphhopper, us-050, sticky-c-lite]
related: ["[[time-aware-routing-engine]]", "[[time-aware-routing-engine-stories]]", "[[sticky-routing-reference]]", "[[edge-depth-table-format]]", "[[graphhopper-backend]]", "[[routing-not-time-aware]]", "[[sprint-plan-2]]", "[[edge-depth-table-java-reader]]"]
---

# Plan: the time-aware weighting and search for `motorbike` and `car` (US-050)

## Context

Acceptance, from [[time-aware-routing-engine-stories]] Story R5. Given a synthetic depth table in the format of [[edge-depth-table-format]], when the four scenarios run for `motorbike` and `car`, with and without a detour, then the results match the reference of `US-047` ([[sticky-routing-reference]]) and the checker finds no crossing of an impassable edge. The search carries the arrival time in its label, applies sticky closure from the departure step with a 10-minute margin, and reads the vehicle limit from the profile.

Out of scope here, and in `US-052` (Sprint 9): the server flag, the request clock (`t0` is the later of `valid_time` and now), the `unknown` answer past the last step, the fallback response flag, and the table source wiring from the server config. `US-051` adds `truck` and `foot`.

## What the pinned GraphHopper offers (commit d7dc1b06, read in the source)

1. `Weighting.calcEdgeWeight(edge, reverse)` has no time argument. A weighting alone cannot know the arrival time, so the time-aware part has to be in the search.
2. `GraphHopper.doCreateRouter` is protected, and `Router.createSolver` and `createFlexSolver` are protected. A `Router` subclass can build a `FlexSolver` with its own `RoutingAlgorithmFactory`. The shadowed `GraphHopperManaged` is not needed for this.
3. `SPTEntry` is a plain class, so a subclass can carry the arrival time, and `PathExtractor.extractPath` works on it.
4. For a mid-edge snap, `QueryGraph` creates virtual edges. `VirtualEdgeIteratorState.getOriginalEdgeKey()` gives back the real edge, and `GHUtility.getEdgeFromEdgeKey` turns the key into the edge id the table is indexed by.

## Design

1. **`StickyClosure`** is the Java form of the Python rule. `closed(edgeId, arrivalSeconds)` is true when a step in `[departure, arrival + margin]` has a depth at or above the limit. Steps before the departure are ignored. The end of the window is included. Margin 600 s.
2. **`TimeAwareDijkstra`** is a unidirectional search over `(weight, time)` labels. The heap orders by weight. A label is dropped when another label at the same node is at least as good in both weight and time. Without that rule a lighter label that arrives later could hide a heavier one that arrives early enough to pass a road that closes. Closure only grows with arrival time, so the dominance rule is exact, and the first label to reach the target is the lightest valid route. It reads the time of each edge from `calcEdgeMillis` (with turn millis when the weighting has turn costs).
3. **The limit comes from the profile**, as the hint `td_limit_cm`. A request carries the departure as the hint `td_departure` (epoch seconds). A request without it, or a profile without a limit, uses the stock search, so nothing changes for it.
4. **Wiring.** `TimeAwareGraphHopper.doCreateRouter` returns a `TimeAwareRouter`. For a time-aware request it builds a `FlexSolver` (LM and CH are skipped, because the lower bounds and shortcuts do not know the time), with an algorithm factory that makes `TimeAwareDijkstra`. The depth table comes from a `Supplier<EdgeDepthTable>` that `US-052` fills from `LatestTableSource`. Tests give it a table directly.
5. **`StickyChecker.findCrossings`** re-walks a route from the edge ids and the edge times and lists every edge entered while closed, as `find_crossings` does in Python. It is independent of the search.

## Steps

Tests first at every step.

1. `StickyClosure`, with the cases of `test_sticky_reference.py`: the window ends, the margin end is included, steps before the departure are ignored, the limit is inclusive.
2. `TimeAwareDijkstra` on an in-memory graph with fixed speeds, so times are exact. The four scenarios of `scenarios.py`, for limits 20 (motorbike) and 30 (car), with and without a detour. A heavier-but-earlier case that only the dominance rule gets right. A differential test against an exhaustive simple-path search on random graphs.
3. `StickyChecker`, and a check that every returned route has no crossing and that the plain shortest route crosses in the blocked scenarios.
4. The wiring, tested through `hopper.route(request)` on the tiny OSM graph with a table written by a test helper, including a snap in the middle of an edge.
5. Latency of the engine on the server is `US-053`. This story prints the visited-node count per request.
6. Docs: [[graphhopper-backend]], [[sticky-routing-reference]], the story files, `TODOS.md`.

## Risks

- **Exactness against speed.** The label set per node can grow. On a flood graph weight is close to time, so the sets stay small, and `US-053` measures it.
- **Virtual edges.** A wrong mapping would read the depth of the wrong edge. The mid-edge test covers it.
- **No LM.** The search is a plain Dijkstra, so it visits more nodes than today's LM search. That is the factor-2 budget of `US-053`.
- **The scenarios run on a synthetic graph, not on real Hanoi roads.** The reference ran on real roads. The Java scenarios copy the reference's four rows on a hand-built corridor. The real-run proof is `US-055`.

## Status history

- **2026-10-05, active.** Plan written after reading the pinned source.
- **2026-10-05, active.** Steps 1 to 4 built and pushed, tests first, 98 module tests. The search is `TimeAwareDijkstra`, hooked in through `TimeAwareGraphHopper.doCreateRouter` and `TimeAwareRouter`. Two facts found on the way: `SpeedWeighting` weighs a minute as 600 and takes millis as distance over speed times 1000 (so tests choose lengths from that), and `VirtualEdgeIterator` is not a `VirtualEdgeIteratorState`, so the search detaches the edge to find the road behind a mid-edge snap (a test fails without it). Five mutations are caught. Added `ScenarioReport` and `scenario-check.sh` for the server evidence. Left: the server run.
- **2026-10-05, done.** `scenario-check.sh` passed on the server (16 of 16, 0 crossings). `US-050` is `Done`.
