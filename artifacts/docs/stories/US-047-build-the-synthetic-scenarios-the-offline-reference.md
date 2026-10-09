---
date_drafted: 2026-09-29
type: user-story
us_id: "US-047"
story_label: "R2"
epic: "[[EP-09-time-aware-routing-engine]]"
status: Done
priority: P0
estimate: M
sprint: 5
subsystem: floodmap-backend, floodmap-frontend
related: ["[[EP-09-time-aware-routing-engine]]", "[[SP-02-routing-engine-foundations|sprint-plan-2]]"]
---

# US-047 Build the synthetic scenarios, the offline reference, and the offline checker

As an engineer, I want a slow reference implementation and a route checker, so the fast engine has
something to be compared against.
Given a synthetic flood on a real Hanoi corridor in `marie-curie/` with a throwaway PostGIS, when the
four scenarios of [[BL-011-routing-not-time-aware|routing-not-time-aware]] run through a time-dependent Dijkstra reference, then the
results match the sticky column of the test table. Given any returned route, when the checker re-walks it
with per-edge times, then it reports whether the route crosses an edge that is impassable at its arrival
step.
Priority: P0. Status: Done. Estimate: M. Sprint: 5. Dependencies: None.
Evidence: ![[us-047-reference-check-output.png|700]]
Details:
1. What: a slow reference search under sticky closure, a route checker, and the four scenarios of the blocker's test table ([[sticky-routing-reference]]).
2. How: `scripts/routing_reference/`. `StickyClosure` applies the PRD's rule: a road is closed when its depth reaches the vehicle limit at any step from the departure to the arrival plus 10 minutes. `earliest_arrival` is Dijkstra over arrival times, which is exact because closures only grow with arrival time. `find_crossings` re-walks a route with per-edge times. `corridor.py` builds a road network from `roads.geojson`, and `scenarios.py` holds the table. Tests came first (54 tests). The search matches an exhaustive search on 300 random graphs, and three deliberate changes to the rule each fail a test.
3. Why: the engine (`US-050`) needs an answer to compare with that does not share its code, and the server proof (`US-055`) needs a checker for the routes GraphHopper returns.
4. Effect: on real Hanoi roads (21.0250, 105.7550 to 21.0255, 105.7620, 15 edges, 1,488 m), all 16 runs (4 scenarios, `motorbike` and `car`, with and without a detour) match the sticky column and the returned routes have 0 crossings. The plain shortest route crosses a closed road in the 8 blocked runs, so the checker catches today's fault. Two departures from the story's wording. No throwaway PostGIS is used, because the scenarios assign depth per edge and need no spatial query. The code lives in `scripts/routing_reference/` and not in `marie-curie/`, which git does not track, so `US-050` and `US-055` can reuse it. The reference has not yet been compared with a GraphHopper response.
