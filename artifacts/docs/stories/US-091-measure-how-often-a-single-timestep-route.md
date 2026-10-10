---
date_drafted: 2026-10-08
type: user-story
us_id: "US-091"
story_label: "2"
epic: "[[EP-20-routing-paper-experiments]]"
status: Done
kind: spike
priority: P1
estimate: M
sprint: 
subsystem: routing, paper
related: ["[[EP-14-routing-paper-experiments]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
title: "Measure how often a single-timestep route meets a closed road on arrival"
---

# US-091 Measure how often a single-timestep route meets a closed road on arrival

As the author of Paper A, I want the violation rate of today's single-timestep routes, so the case for time-aware routing is a number and not an argument.
Given pairs sampled inside the model border, in three length classes (under 2 km, 2 to 5 km, over 5 km), for each of the four vehicles and each departure step, when the backend plans each route with the single-timestep model (the flag off) and the checker re-walks it with the arrival time of each edge, then a result file records the violation rate by vehicle, trip length class, departure step, and storm stage (cold start, one hour, three hours).
The file reports three arrival-step rules side by side: the step at or before the arrival, the nearest step, and the worse of the two around it.
It also records the severity (depth over the limit at the worst edge, and the number of violating edges) and the time to the first violation along the route.
The story builds the harness that `US-092` reuses: the pair sampler, the call that plans a route, the re-walk, and the result writer.
It sits on `scripts/routing_reference/` and the crossings check of `scripts/routing_proof/`.
The sticky engine is run on the same pairs as a test.
Its violation count must be 0, so the experiment also checks the engine.
Arrival times assume free flow, so the story adds one sensitivity case that slows travel on deep edges, labelled as a sensitivity case.
Needs no new engine.
Dependencies: `US-047` (the reference and the checker, `Done`), `US-050` and `US-052` (the engine behind the flag, `Done`), and the depth tables of the 12-hour replay of `US-089` (copied before retention removes them, see rule 5).
The server run reads the engine proof of `US-055`, which is `In progress`.
The sticky-engine check inside this story needs the same server state that `US-055` proved on 2026-10-07.
## Status history

- **2026-10-10, carried from the retired TODOS note.** The harness is in `scripts/routing_experiments/` (41 tests pass).
  Three things to know.
  First, the runner walks engine routes from the time of the request since `US-096`.
  Second, the sticky engine cannot be checked on the old replay tables, because the backend departs at the later of the step time and now, so the sticky check needs live tables.
  Third, the single-timestep plan reads the database flood areas and the re-walk reads the edge depth table of the same run, which are two depth sources, and the result file must say so.
- **2026-10-10, preliminary run on the 12-hour data (not the result).** The harness plans through the backend, and the backend keeps flood areas for the newest 8 runs only (`FLOOD_EXTENT_KEEP_RUNS=8`), so only the last 8 runs of the second replay (23:15 to 01:00 +07) can be planned.
  `experiment.py run --model single_timestep` on those 8 tables, 30 pairs (10 per length class, seed 1), 4 vehicles, departure steps 0 and 1, against the backend with the flag off (`model_check`: 0 routes of another model) took 11 min 42 s and planned 1,486 routes (434 of 1,920 had no route).
  Result file: `marie-curie/us-091/single_timestep_late_seed1.json`.
  Violation rate under the rule "step at or before the arrival": 119 of 1,486 routes (8.0 percent), 120 under the nearest step, and 139 under the worse of the two.
  By vehicle it is 18.2 percent (car), 6.3 (truck), 3.8 (foot), and 3.2 (motorbike).
  By length class it is 13.5 percent under 2 km, 2.8 from 2 to 5 km, and 7.9 over 5 km.
  By departure step it is 7.4 (step 0) and 8.6 (step 1).
  The sticky rule would close an edge on 120 of the 1,486 routes.
  Limits: one stage only (late storm, no cold-start, one-hour, or three-hour stages), 30 pairs, and free-flow arrival times.
  The depth sources differ (backend flood areas to plan, edge depth tables to re-walk).
  The sticky engine check on the same pairs is not done.
  The remaining stages need a replay with `FLOOD_EXTENT_KEEP_RUNS` raised (about 60).
- **2026-10-10, done.** The product owner gave the go, and the replay tables answered the question: the single-timestep rate by stage, vehicle, length class, and departure step, the live sticky check, and one labelled sensitivity case.
  The decision is [[decision-log|D-031]].

## Evidence and details

**Evidence:** rendered output of the single-timestep result (`marie-curie/us-091/single_timestep_seed1.json`, read 2026-10-10 18:55 +07) and of the three live sticky readings (read 18:41 +07).

![[us-091-single-timestep-result-output.png|900]]

![[us-091-live-sticky-mid-step-output.png|900]]

**Details:**

1. Files. The main run is `marie-curie/us-091/single_timestep_seed1.json`, with `single_timestep_summary.txt` and `single_timestep_severity.txt` beside it. The sensitivity case is `single_timestep_slow_3h_seed1.json`. The live sticky readings are `sticky_cold_seed1.json`, `sticky_1h_seed1.json`, and `sticky_3h_seed1.json`. The main run ran on the server worker from 18:22 to 18:49 +07 with the backend flag off.
2. Setup. The 60 pairs (20 per length class, seed 1) are in `pairs60_seed1.json`. The run used 4 vehicles and departure steps 0 and 1. Each of the cold, one-hour, and three-hour stages is one table: 2026-10-10 at 05:15, 06:15, and 08:15 +07. The late stage is the last 8 runs, 16:30 to 18:15 +07. The vehicle limits in the file are 20 cm (motorbike), 30 cm (car), 35 cm (truck), and 40 cm (foot).
3. Rule and count. Under the rule "step at or before the arrival", 307 of 3,911 routes violate, which is 7.8 percent. The nearest-step rule gives 310 (7.9 percent), and the worse-of-two rule gives 346 (8.8 percent).
4. Dropped requests. 1,369 of 5,280 requests had no route (25.9 percent). They are reported as dropped, not as violations and not as routes. SPR-013 estimated 23 percent before the run, and the count replaces that estimate.
5. By storm stage: cold 30 of 423 routes (7.1 percent), one hour 15 of 402 (3.7 percent), three hours 49 of 376 (13.0 percent), and late 213 of 2,710 (7.9 percent).
6. By vehicle: car 102 of 947 (10.8 percent), motorbike 90 of 862 (10.4 percent), foot 71 of 1,205 (5.9 percent), and truck 44 of 897 (4.9 percent).
7. By trip length: under 2 km 72 of 1,337 (5.4 percent), 2-5 km 91 of 1,170 (7.8 percent), and over 5 km 144 of 1,404 (10.3 percent).
8. By departure step: step 0 155 of 1,956 (7.9 percent), and step 1 152 of 1,955 (7.8 percent).
9. Severity of the 307 violating routes. The depth over the vehicle limit at the worst edge has a median of 16 cm, a 75th percentile of 24 cm, and a maximum of 140 cm. A violating route has a median of 1 violating edge, a mean of 1.0, and a maximum of 4.
10. Time to the first violation, counted from departure: median 513 s, 25th percentile 218 s, and 75th percentile 644 s.
11. Live sticky check. The engine ran on the same 60 pairs with departure steps 0 to 5, and `TIME_AWARE_ROUTING` was on for `floodmap-backend` only. It planned 1,292, 1,253, and 1,215 routes at the cold, one-hour, and three-hour tables, with 0 crossings in each. The readings had 636 departures between two steps (219, 212, and 205). The screenshot gives one example: a request valid at 06:15 +07 was walked from 06:16:55, and the engine reported step 06:15.
12. Limit of the sticky check. Zero crossings holds under the two rules that the sticky margin covers, step at or before and nearest. The worse-of-two rule gives 25, 33, and 11 violations at the three tables, and the margin does not cover that rule.
    The `sticky_check` block inside the single-timestep files (316 routes in the main run, 49 in the sensitivity run) counts flag-off routes that a sticky closure would cross. It is not the engine check, and its `passed: false` is expected for those routes.
13. Sensitivity case, labelled as a sensitivity case. Edges at 20 cm or deeper take 2 times their free-flow time, on the 3-hour table, with 60 pairs, steps 0 and 1, and the flag off. It gives 376 routes, of which 49 violate under the at-or-before and nearest rules and 50 under the worse-of-two rule. The free-flow 3-hour stage has 49 of 376 under the same rules, so slowing travel in deep water did not change the count on this table.
14. Limits. The main result assumes free-flow arrival times. Each of the cold, one-hour, and three-hour stages is one table, and the late stage is 8 tables. The single-timestep run used departure steps 0 and 1, where SPR-013 had planned 0 to 6, and the sticky check used steps 0 to 5.
    The two depth sources are the backend's flood areas, which plan each route, and the edge depth table of the same run, which the re-walk reads. The backend keeps flood areas for `FLOOD_EXTENT_KEEP_RUNS` runs, which is 100 on the server.
15. Decision. [[decision-log|D-031]] records that the measured rate supports time-aware routing. Whether `TIME_AWARE_ROUTING` stays on for good is the product owner's decision (open decision 7 in [[SPR-013-prove-the-storm-replay-and-finish-the-replay-stories|SPR-013]]).
16. Blocker. The live readings of item 11 resolve [[BL-026-sticky-closure-clock-anchored-at-floored-departure|BL-026]].
