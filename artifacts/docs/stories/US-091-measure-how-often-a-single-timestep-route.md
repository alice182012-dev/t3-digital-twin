---
date_drafted: 2026-10-08
type: user-story
us_id: "US-091"
story_label: "2"
epic: "[[EP-20-routing-paper-experiments]]"
status: In progress
kind: spike
priority: P1
estimate: M
sprint: 
subsystem: routing, paper
related: ["[[EP-14-routing-paper-experiments]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
title: "Measure how often a single-timestep route meets a closed road on arrival"
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
Dependencies: `US-047` (the reference and the checker, `Done`), `US-050` and `US-052` (the engine behind the flag,
`Done`), and the depth tables of the 12-hour replay of `US-089` (copied before retention removes them, see rule 5).
The server run reads the engine proof of `US-055`, which is `In progress`. The sticky-engine check inside this story
needs the same server state that `US-055` proved on 2026-10-07.
Evidence: None yet.
- **2026-10-10, carried from the retired TODOS note.** The harness is in `scripts/routing_experiments/` (41 tests pass). Three things to know. First, the runner walks engine routes from the time of the request since `US-096`. Second, the sticky engine cannot be checked on the old replay tables, because the backend departs at the later of the step time and now, so the sticky check needs live tables. Third, the single-timestep plan reads the database flood areas and the re-walk reads the edge depth table of the same run, which are two depth sources, and the result file must say so.
- **2026-10-10, preliminary run on the 12-hour data (not the result).** The harness plans through the backend, and the backend keeps flood areas for the newest 8 runs only (`FLOOD_EXTENT_KEEP_RUNS=8`), so only the last 8 runs of the second replay (23:15 to 01:00 +07) can be planned. `experiment.py run --model single_timestep` on those 8 tables, 30 pairs (10 per length class, seed 1), 4 vehicles, departure steps 0 and 1, against the backend with the flag off (`model_check`: 0 routes of another model) took 11 min 42 s and planned 1,486 routes (434 of 1,920 had no route). Result file: `marie-curie/us-091/single_timestep_late_seed1.json`. Violation rate under the rule "step at or before the arrival": 119 of 1,486 routes (8.0 percent), 120 under the nearest step, and 139 under the worse of the two. By vehicle it is 18.2 percent (car), 6.3 (truck), 3.8 (foot), and 3.2 (motorbike). By length class it is 13.5 percent under 2 km, 2.8 from 2 to 5 km, and 7.9 over 5 km. By departure step it is 7.4 (step 0) and 8.6 (step 1). The sticky rule would close an edge on 120 of the 1,486 routes. Limits: one stage only (late storm, no cold-start, one-hour, or three-hour stages), 30 pairs, and free-flow arrival times. The depth sources differ (backend flood areas to plan, edge depth tables to re-walk). The sticky engine check on the same pairs is not done. The remaining stages need a replay with `FLOOD_EXTENT_KEEP_RUNS` raised (about 60).
