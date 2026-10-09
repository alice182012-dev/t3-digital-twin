---
date_drafted: 2026-10-08
type: user-story
us_id: "US-091"
story_label: "2"
epic: "[[EP-14-routing-paper-experiments]]"
status: In progress
priority: P1
estimate: M
sprint: 12
subsystem: routing, paper
related: ["[[EP-14-routing-paper-experiments]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
---

# US-091 Measure how often a single-timestep route meets a closed road on arrival

As the author of Paper A, I want the violation rate of today's single-timestep routes, so the case for time-aware
routing is a number and not an argument.
Given pairs sampled inside the model border, in three length classes (under 2 km, 2 to 5 km, over 5 km), for each of
the four vehicles and each departure step, when the backend plans each route with the single-timestep model (the
flag off) and the checker re-walks it with the arrival time of each edge, then a result file records the violation
rate by vehicle, trip length class, departure step, and storm stage (cold start, one hour, three hours). The file
reports three arrival-step rules side by side: the step at or before the arrival, the nearest step, and the worse of
the two around it. It also records the severity (depth over the limit at the worst edge, and the number of violating
edges) and the time to the first violation along the route.
The story builds the harness that `US-092` reuses: the pair sampler, the call that plans a route, the re-walk, and
the result writer. It sits on `scripts/routing_reference/` and the crossings check of `scripts/routing_proof/`.
The sticky engine is run on the same pairs as a test. Its violation count must be 0, so the experiment also checks
the engine. Arrival times assume free flow, so the story adds one sensitivity case that slows travel on deep
edges, labelled as a sensitivity case.
Needs no new engine.
Priority: P1. Status: In progress. Estimate: M. Sprint: 12 ([[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]; 2026-12-07 to 2026-12-13).
Dependencies: `US-047` (the reference and the checker, `Done`), `US-050` and `US-052` (the engine behind the flag,
`Done`), and the depth tables of the 12-hour replay of `US-089` (copied before retention removes them, see rule 5).
The server run reads the engine proof of `US-055`, which is `In progress`. The sticky-engine check inside this story
needs the same server state that `US-055` proved on 2026-10-07.
Evidence: None yet.
